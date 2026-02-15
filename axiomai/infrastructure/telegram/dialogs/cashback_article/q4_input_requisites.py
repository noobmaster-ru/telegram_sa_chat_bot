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
    WB_CHANNEL_NAME,
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
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    buyer_id = dialog_manager.dialog_data.get("buyer_id")

    if not buyer_id:
        await message.answer("К сожалению что-то пошло не так, попробуйте пройти процесс заново.")
        await dialog_manager.done()
        return

    buyer = await buyer_gateway.get_buyer_by_id(buyer_id)

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    requisites = message.text.strip()

    if buyer.amount:
        dialog_manager.dialog_data["amount"] = buyer.amount

    if card_match := CARD_PATTERN.search(requisites):
        dialog_manager.dialog_data["card_number"] = CARD_CLEAN_RE.sub("", card_match.group())
    if (amount_match := AMOUNT_PATTERN.search(requisites)) and (not buyer.amount):
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
async def on_confirm_requisites(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    superbanking: FromDishka[Superbanking],
    create_superbanking_payment: FromDishka[CreateSuperbankingPayment],
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    buyer_id = dialog_manager.dialog_data.get("buyer_id")
    logger.info("on_confirm_requisites started: buyer_id=%s", buyer_id)
    if not buyer_id:
        logger.warning("on_confirm_requisites aborted: missing buyer_id in dialog_data")
        await callback.message.answer("К сожалению что-то пошло не так, попробуйте пройти процесс заново.")
        await dialog_manager.done()
        return

    await callback.message.edit_text(f"{callback.message.text[:-1]}: <b>Да</b>")
    await callback.message.answer("Ожидайте выплату в ближайшее время, спасибо ☺")
    
    
    business_connection_id = callback.message.business_connection_id if callback.message else None
    logger.info(
        "on_confirm_requisites resolving cabinet: buyer_id=%s, business_connection_id=%s",
        buyer_id,
        business_connection_id,
    )
    cabinet = (
        await cabinet_gateway.get_cabinet_by_business_connection_id(business_connection_id)
        if business_connection_id
        else None
    )
    if not cabinet or not cabinet.is_superbanking_connect:
        await _save_requisites_without_superbanking(
            buyer_id=buyer_id,
            dialog_manager=dialog_manager,
            buyer_gateway=buyer_gateway,
            transaction_manager=transaction_manager,
        )
        logger.info(
            "on_confirm_requisites skipping Superbanking: buyer_id=%s, cabinet_found=%s, is_superbanking_connect=%s",
            buyer_id,
            bool(cabinet),
            getattr(cabinet, "is_superbanking_connect", None),
        )
        await callback.message.answer(f"Подписывайтесь на наш канал {WB_CHANNEL_NAME} , там будет много интересных товаров")
        await dialog_manager.done()
        return

    order_number, payout_error_message = await _create_superbanking_payout(
        buyer_id=buyer_id,
        dialog_manager=dialog_manager,
        create_superbanking_payment=create_superbanking_payment,
    )
    if order_number is None:
        await callback.message.answer(payout_error_message)
        await callback.message.answer(f"Подписывайтесь на наш канал {WB_CHANNEL_NAME} , там будет много интересных товаров")
        await dialog_manager.done()
        return

    if order_number:
        logger.info(
            "on_confirm_requisites scheduling receipt check: buyer_id=%s, order_number=%s",
            buyer_id,
            order_number,
        )
        task = asyncio.create_task(
            _send_receipt_after_confirm(
                superbanking=superbanking,
                message=callback.message,
                order_number=order_number,
                buyer_id=buyer_id,
            )
        )
        task.add_done_callback(lambda _: None)
    await callback.message.answer(f"Подписывайтесь на наш канал {WB_CHANNEL_NAME} , там будет много интересных товаров")
    await dialog_manager.done()


async def _save_requisites_without_superbanking(
    *,
    buyer_id: int,
    dialog_manager: DialogManager,
    buyer_gateway: BuyerGateway,
    transaction_manager: TransactionManager,
) -> None:
    buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
    if not buyer:
        logger.warning(
            "on_confirm_requisites could not save requisites: buyer not found, buyer_id=%s",
            buyer_id,
        )
        return

    if phone_number := dialog_manager.dialog_data.get("phone_number"):
        buyer.phone_number = phone_number
    if bank := dialog_manager.dialog_data.get("bank"):
        buyer.bank = bank
    if amount := dialog_manager.dialog_data.get("amount"):
        with contextlib.suppress(ValueError, TypeError):
            if not buyer.amount:
                buyer.amount = int(amount)

    await transaction_manager.commit()
    logger.info(
        "on_confirm_requisites saved requisites without Superbanking payout: buyer_id=%s",
        buyer_id,
    )


async def _create_superbanking_payout(
    *,
    buyer_id: int,
    dialog_manager: DialogManager,
    create_superbanking_payment: CreateSuperbankingPayment,
) -> tuple[str | None, str]:
    logger.info("on_confirm_requisites creating Superbanking payment: buyer_id=%s", buyer_id)
    try:
        order_number = await create_superbanking_payment.execute(
            buyer_id=buyer_id,
            phone_number=dialog_manager.dialog_data.get("phone_number"),
            bank=dialog_manager.dialog_data.get("bank"),
            amount=dialog_manager.dialog_data.get("amount"),
        )
    except CreatePaymentError:
        logger.warning("on_confirm_requisites create_payment failed: buyer_id=%s", buyer_id)
        return None, "Не удалось инициировать выплату. Мы свяжемся с вами."
    except SignPaymentError:
        logger.warning("on_confirm_requisites sign_payment failed: buyer_id=%s", buyer_id)
        return None, "Не удалось отправить выплату. Мы свяжемся с вами."
    except Exception:
        logger.exception("Failed to create Superbanking payout for buyer_id=%s", buyer_id)
        return None, "Не удалось инициировать выплату. Мы свяжемся с вами."

    logger.info(
        "on_confirm_requisites Superbanking payment created: buyer_id=%s, order_number=%s",
        buyer_id,
        order_number,
    )
    return order_number, ""


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
