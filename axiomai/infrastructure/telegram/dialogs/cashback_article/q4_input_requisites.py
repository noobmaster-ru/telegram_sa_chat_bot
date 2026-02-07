import asyncio
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
) -> None:
    buyer_id = dialog_manager.dialog_data.get("buyer_id")
    if not buyer_id:
        await callback.message.answer("К сожалению что-то пошло не так, попробуйте пройти процесс заново.")
        await dialog_manager.done()
        return

    await callback.message.edit_text(f"{callback.message.text[:-1]}: <b>Да</b>")
    await callback.message.answer("Ожидайте выплату в ближайшее время, спасибо ☺")
    
    try:
        order_number = await create_superbanking_payment.execute(
            buyer_id=buyer_id,
            phone_number=dialog_manager.dialog_data.get("phone_number"),
            bank=dialog_manager.dialog_data.get("bank"),
            amount=dialog_manager.dialog_data.get("amount"),
        )
    except CreatePaymentError:
        await callback.message.answer("Не удалось инициировать выплату. Мы свяжемся с вами.")
        await dialog_manager.done()
        return
    except SignPaymentError:
        await callback.message.answer("Не удалось отправить выплату. Мы свяжемся с вами.")
        await dialog_manager.done()
        return
    except Exception:
        logger.exception("Failed to create Superbanking payout for buyer_id=%s", buyer_id)
        await callback.message.answer("Не удалось инициировать выплату. Мы свяжемся с вами.")
        await dialog_manager.done()
        return

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
