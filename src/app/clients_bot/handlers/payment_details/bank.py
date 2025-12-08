import re
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage


from src.app.bot.states.client import ClientStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.utils.last_activity import update_last_activity
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.tools.string_converter_class import StringConverter
from src.core.config import constants

from .router import router


@router.business_message(StateFilter(ClientStates.waiting_for_bank))
async def handle_bank_name(
    message: Message, 
    state: FSMContext,
    spreadsheet: GoogleSheetClass
):
    text = message.text.strip()
    telegram_id = message.from_user.id
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    bank_match = re.search(constants.bank_pattern, text, flags=re.IGNORECASE)
    bank = bank_match.group(0).capitalize() if bank_match else None
    await state.update_data(bank=bank)

    data = await state.get_data()
    msg = None
    if data.get("amount"):
        if data.get('card_number'):
            if data.get('phone_number'):
                text = (
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?"
                )
                msg = await message.answer(
                    text=StringConverter.escape_markdown_v2(text),
                    parse_mode="MarkdownV2",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return
            else:
                text = (
                    f"📩 Получены реквизиты:\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?"
                )
                msg = await message.answer(
                    text=StringConverter.escape_markdown_v2(text),
                    parse_mode="MarkdownV2",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return
        if data.get('phone_number'):
            if data.get('card_number'):
                text = (
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?"
                )
                msg = await message.answer(
                    text=StringConverter.escape_markdown_v2(text),
                    parse_mode="MarkdownV2",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return 
            else:
                text = (
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?"
                )
                msg = await message.answer(
                    text=StringConverter.escape_markdown_v2(text),
                    parse_mode="MarkdownV2",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return
    else:
        text = (
            f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей"
        )
        msg = await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_amount)
        await update_last_activity(state, msg)
        return