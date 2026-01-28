import contextlib
from typing import Any

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram_dialog import inject
from redis.asyncio import Redis

from axiomai.constants import (
    AMOUNT_PATTERN,
    BANK_PATTERN,
    CARD_CLEAN_RE,
    CARD_PATTERN,
    PHONE_PATTERN,
)
from axiomai.infrastructure.superbanking import Superbanking
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import _update_buyer_field


@inject
async def on_input_requisites(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    superbanking: FromDishka[Superbanking],
    redis: FromDishka[Redis],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    requisites = message.text.strip()

    gpt_amount_key = f"gpt_amount:{message.from_user.id}:{message.chat.id}"
    gpt_amount = await redis.get(gpt_amount_key)
    if gpt_amount:
        dialog_manager.dialog_data["amount"] = gpt_amount.decode() if isinstance(gpt_amount, bytes) else gpt_amount

    if card_match := CARD_PATTERN.search(requisites):
        dialog_manager.dialog_data["card_number"] = CARD_CLEAN_RE.sub("", card_match.group())
    if (amount_match := AMOUNT_PATTERN.search(requisites)) and (not gpt_amount):
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
    di_container: FromDishka[AsyncContainer],
) -> None:

    buyer_id = dialog_manager.dialog_data.get("buyer_id")
    if buyer_id:
        update_fields = {}
        if dialog_manager.dialog_data.get("phone_number"):
            update_fields["phone_number"] = dialog_manager.dialog_data["phone_number"]
        if dialog_manager.dialog_data.get("bank"):
            update_fields["bank"] = dialog_manager.dialog_data["bank"]
        if dialog_manager.dialog_data.get("amount"):
            with contextlib.suppress(ValueError, TypeError):
                update_fields["amount"] = int(dialog_manager.dialog_data["amount"])
        if update_fields:
            await _update_buyer_field(di_container, buyer_id, **update_fields)

    await callback.message.edit_text(f"{callback.message.text[:-1]}: <b>Да</b>")
    await callback.message.answer("Ожидайте выплату в ближайшее время, спасибо ☺")
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
