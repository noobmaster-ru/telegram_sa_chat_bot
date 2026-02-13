import asyncio
import contextlib
import logging
from typing import Any
from urllib import error

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, URLInputFile
from aiogram_dialog import DialogManager, ShowMode
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.exceptions.superbanking import CreatePaymentError, SignPaymentError
from axiomai.application.interactors.create_superbanking_payment import CreateSuperbankingPayment
from axiomai.constants import (
    AMOUNT_PATTERN,
    BANK_PATTERN,
    CARD_CLEAN_RE,
    CARD_PATTERN,
    PHONE_PATTERN,
    TIME_SLEEP_BEFORE_CONFIRM_PAYMENT,
)
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.superbanking import Superbanking

logger = logging.getLogger(__name__)


@inject
async def on_input_requisites(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    superbanking: FromDishka[Superbanking],
    buyer_gateway: FromDishka[BuyerGateway],
    cabinet_gateway: FromDishka[CabinetGateway],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(message.business_connection_id)
    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(message.from_user.id, cabinet.id)
    completed_buyers = [b for b in buyers if b.is_cut_labels]

    if not completed_buyers:
        await message.answer("К сожалению что-то пошло не так, попробуйте пройти процесс заново.")
        await dialog_manager.done()
        return

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    requisites = message.text.strip()

    # Считаем общую сумму из buyers
    total_amount = sum(b.amount or 0 for b in completed_buyers)
    if total_amount:
        dialog_manager.dialog_data["amount"] = total_amount

    if card_match := CARD_PATTERN.search(requisites):
        dialog_manager.dialog_data["card_number"] = CARD_CLEAN_RE.sub("", card_match.group())
    if (amount_match := AMOUNT_PATTERN.search(requisites)) and (not total_amount):
        dialog_manager.dialog_data["amount"] = amount_match.group(1)
    if phone_match := PHONE_PATTERN.search(requisites):
        dialog_manager.dialog_data["phone_number"] = phone_match.group()
    if bank_match := BANK_PATTERN.search(requisites):
        bank_alias = bank_match.group()
        bank_name_rus = superbanking.get_bank_name_rus(bank_alias)
        dialog_manager.dialog_data["bank"] = bank_name_rus or bank_alias.capitalize()
    elif bank_name_rus := superbanking.get_bank_name_rus(requisites):
        dialog_manager.dialog_data["bank"] = bank_name_rus

    await dialog_manager.show(ShowMode.SEND)


@inject
async def on_confirm_requisites(  # noqa: C901
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    superbanking: FromDishka[Superbanking],
    create_superbanking_payment: FromDishka[CreateSuperbankingPayment],
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    business_connection_id = callback.message.business_connection_id if callback.message else None

    cabinet = (
        await cabinet_gateway.get_cabinet_by_business_connection_id(business_connection_id)
        if business_connection_id
        else None
    )

    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(callback.from_user.id, cabinet.id) if cabinet else []
    completed_buyers = [b for b in buyers if b.is_cut_labels]

    if not completed_buyers:
        logger.warning("on_confirm_requisites aborted: no completed buyers")
        await callback.message.answer("К сожалению что-то пошло не так, попробуйте пройти процесс заново.")
        await dialog_manager.done()
        return

    buyer_ids = [b.id for b in completed_buyers]
    logger.info("on_confirm_requisites started: buyer_ids=%s", buyer_ids)

    await callback.message.edit_text(f"{callback.message.text[:-1]}: <b>Да</b>")
    await callback.message.answer("Ожидайте выплату в ближайшее время, спасибо ☺")
    
    phone_number = dialog_manager.dialog_data.get("phone_number")
    bank = dialog_manager.dialog_data.get("bank")
    total_amount = dialog_manager.dialog_data.get("amount")

    if not cabinet or not cabinet.is_superbanking_connect:
        # Сохраняем реквизиты для всех buyers
        for buyer_id in buyer_ids:
            buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
            if buyer:
                if phone_number:
                    buyer.phone_number = phone_number
                if bank:
                    buyer.bank = bank
                if total_amount and not buyer.amount:
                    with contextlib.suppress(ValueError, TypeError):
                        buyer.amount = int(total_amount)
        await transaction_manager.commit()
        logger.info(
            "on_confirm_requisites saved requisites without Superbanking payout: buyer_ids=%s",
            buyer_ids,
        )
        await dialog_manager.done()
        return

    # Создаём выплаты для каждого buyer
    logger.info("on_confirm_requisites creating Superbanking payments: buyer_ids=%s", buyer_ids)
    
    for buyer_id in buyer_ids:
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        if not buyer:
            continue
            
        buyer_amount = buyer.amount
        if not buyer_amount:
            logger.warning("Skipping Superbanking payment for buyer_id=%s: no amount", buyer_id)
            continue

        try:
            order_number = await create_superbanking_payment.execute(
                buyer_id=buyer_id,
                phone_number=phone_number,
                bank=bank,
                amount=buyer_amount,
            )
            logger.info(
                "on_confirm_requisites Superbanking payment created: buyer_id=%s, order_number=%s",
                buyer_id,
                order_number,
            )
            
            if order_number:
                task = asyncio.create_task(
                    _send_receipt_after_confirm(
                        superbanking=superbanking,
                        message=callback.message,
                        order_number=order_number,
                        buyer_id=buyer_id,
                    )
                )
                task.add_done_callback(lambda _: None)
                
        except CreatePaymentError:
            logger.warning("on_confirm_requisites create_payment failed: buyer_id=%s", buyer_id)
        except SignPaymentError:
            logger.warning("on_confirm_requisites sign_payment failed: buyer_id=%s", buyer_id)
        except Exception:
            logger.exception("Failed to create Superbanking payout for buyer_id=%s", buyer_id)

    await dialog_manager.done()


async def _send_receipt_after_confirm(
    *,
    superbanking: Superbanking,
    message: Message,
    order_number: str,
    buyer_id: int,
) -> None:
    try:
        await asyncio.sleep(TIME_SLEEP_BEFORE_CONFIRM_PAYMENT)
        check_url = superbanking.confirm_operation(order_number=order_number)
        pdf_file = URLInputFile(
            check_url,
            filename="Чек.pdf",
        )
        await message.answer_document(
            document=pdf_file,
            caption="Чек по выплате",
        )
    except (ValueError, error.HTTPError, error.URLError):
        logger.exception(
            "Failed to confirm_operation() Superbanking payout for buyer_id=%s",
            buyer_id,
        )
        await message.answer("Чек будет доступен чуть позже. Мы пришлём его дополнительно.")


async def on_decline_requisites(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager) -> None:
    if "bank" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["bank"]
    if "phone_number" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["phone_number"]
    if "card_number" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["card_number"]

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "❌ Хорошо, давайте попробуем ещё раз (по порядку запишем всё заново)\n"
        "Отправьте номер телефона в формате:\n\n<code>+7910XXXXXXX</code>"
    )

    dialog_manager.show_mode = ShowMode.NO_UPDATE
