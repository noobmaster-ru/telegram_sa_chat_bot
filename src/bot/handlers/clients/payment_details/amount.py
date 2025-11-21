import re
import logging

from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage


from src.bot.states.client import ClientStates
from src.core.constants import amount_pattern
from src.services.google_sheets_class import GoogleSheetClass
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.utils.last_activity import update_last_activity

from .router import router

@router.business_message(StateFilter(ClientStates.waiting_for_amount))
async def handle_amount(
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
    amounts = re.findall(amount_pattern, text, flags=re.IGNORECASE)
    amount = amounts[0] if amounts else None
    await state.update_data(amount=amount)

    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )  
    data = await state.get_data()
    msg = None
    if data.get('bank'):
        if data.get('card_number'):
            if data.get('phone_number'):
                msg = await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return
            else:
                msg = await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return
        elif data.get('phone_number'):
            if data.get('card_number'):
                msg = await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return
            else:
                msg = await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return
    else:
        msg = await message.answer(
            f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
            parse_mode="Markdown"
        )  
        await state.set_state(ClientStates.waiting_for_bank)
        await update_last_activity(state, msg)
