import contextlib
import logging
from typing import Any
import asyncio

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, URLInputFile
from aiogram_dialog import DialogManager, ShowMode
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.constants import (
    AMOUNT_PATTERN, 
    BANK_PATTERN, 
    CARD_CLEAN_RE, 
    CARD_PATTERN, 
    PHONE_PATTERN,
    SUPERBANKING_ORDER_PREFIX,
    TIME_SLEEP_BEFORE_CONFIRM_PAYMENT
)
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.superbanking_payout import SuperbankingPayoutGateway
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
    buyer_gateway: FromDishka[BuyerGateway],
    superbanking_payout_gateway: FromDishka[SuperbankingPayoutGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    buyer_id = dialog_manager.dialog_data.get("buyer_id")
    if not buyer_id:
        await callback.message.answer("К сожалению что-то пошло не так, попробуйте пройти процесс заново.")
        await dialog_manager.done()
        return

    buyer = await buyer_gateway.get_buyer_by_id(buyer_id)

    if dialog_manager.dialog_data.get("phone_number"):
        buyer.phone_number = dialog_manager.dialog_data["phone_number"]
    if dialog_manager.dialog_data.get("bank"):
        buyer.bank = dialog_manager.dialog_data["bank"]
    if dialog_manager.dialog_data.get("amount"):
        with contextlib.suppress(ValueError, TypeError):
            if not buyer.amount:
                buyer.amount = int(dialog_manager.dialog_data["amount"])

    await callback.message.edit_text(f"{callback.message.text[:-1]}: <b>Да</b>")
    await callback.message.answer("Ожидайте выплату в ближайшее время, спасибо ☺")
    
    if buyer.phone_number and buyer.bank and buyer.amount:
        # создаём запись о выплате в таблице superbanking и берём id оттуда,
        #   чтобы сформировать уникальный orderNumber в create_payment()
        payout = await superbanking_payout_gateway.create_payout(
            buyer_id=buyer.id,
            nm_id=buyer.nm_id,
            phone_number=buyer.phone_number,
            bank=buyer.bank,
            amount=buyer.amount,
        )
        await transaction_manager.commit()
        
        # orderNumber нужен в confirm_operation(), он должен быть уникальным и не повторяться
        order_number = f"{SUPERBANKING_ORDER_PREFIX}{payout.id}"

        try:
            cabinet_transaction_id = superbanking.create_payment(
                phone_number=buyer.phone_number,
                bank_name_rus=buyer.bank,
                amount=buyer.amount,
                order_number=order_number,
            )
            try:
                is_succeed_payment = superbanking.sign_payment(
                    cabinet_transaction_id=cabinet_transaction_id     
                )
                if not is_succeed_payment:
                    raise ValueError("Superbanking sign_payment() returned False")

                await asyncio.sleep(TIME_SLEEP_BEFORE_CONFIRM_PAYMENT)

                try:
                    check_url = superbanking.confirm_operation(order_number=order_number)
                    # Создаем объект файла из ссылки
                    pdf_file = URLInputFile(
                        check_url,
                        filename="Чек.pdf"  
                    )
                    await callback.message.answer_document(
                        document=pdf_file,
                        caption="Чек по выплате",
                    )
                except Exception:
                    logger.exception("Failed to confirm_operation() Superbanking payout for buyer_id=%s", buyer_id)
                    await callback.message.answer("Чек будет доступен чуть позже. Мы пришлём его дополнительно.")
            except Exception:
                logger.exception("Failed to sign_payment() Superbanking payout for buyer_id=%s", buyer_id)
                await callback.message.answer("Не удалось отправить выплату. Мы свяжемся с вами.")
                await dialog_manager.done()
                return
        except Exception:
            logger.exception("Failed to create_payment() Superbanking payout for buyer_id=%s", buyer_id)
            await callback.message.answer("Не удалось инициировать выплату. Мы свяжемся с вами.")
            await dialog_manager.done()
            return
    else:
        await transaction_manager.commit()


    await dialog_manager.done()


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
