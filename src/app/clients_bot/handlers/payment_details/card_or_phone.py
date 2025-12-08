import re
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage


from src.app.bot.states.client import ClientStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.utils.last_activity import update_last_activity
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass

from src.core.config import constants

from .router import router

@router.business_message(StateFilter(ClientStates.waiting_for_card_or_phone_number))
async def handle_card_or_phone_number(
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
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        text=text
    )
    
    # --- Поиск данных ---
    cards = re.findall(constants.card_pattern, text)
    phones = re.findall(constants.phone_pattern, text)
    
    # Запись в переменные (берём первое найденное или None)
    card_number = cards[0] if cards else None
    phone_number = phones[0] if phones else None

    # --- Сохраняем найденное в FSM ---
    data = await state.get_data()
    # logging.info(data) - {} выводит
    if card_number:
        data["card_number"] = re.sub(r"[ -]", "", card_number)
    if phone_number:
        data["phone_number"] = re.sub(r"^\+?8", "7", phone_number)  # нормализуем формат
    await state.update_data(**data)
    

    data = await state.get_data()
    msg = None
    if data.get('bank'):
        if data.get('card_number'):
            if data.get('amount'):
                msg = await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер карты: `{data.get('card_number', '')}`\n"
                    f"Банк: {data.get('bank', '')}\n"
                    f"Сумма: `{data.get('amount', '')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="MarkdownV2",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return 
            else:
                msg = await message.answer(
                    f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                    parse_mode="MarkdownV2"
                )  
                await state.set_state(ClientStates.waiting_for_amount)
                await update_last_activity(state, msg)
                return 
        if data.get('phone_number'):
            if data.get('amount'):
                msg = await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number', '')}`\n"
                    f"Банк: {data.get('bank', '')}\n"
                    f"Сумма: `{data.get('amount', '')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="MarkdownV2",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(ClientStates.confirming_requisites)
                await update_last_activity(state, msg)
                return 
            else:
                msg = await message.answer(
                    f"💬 Пожалуйста, отправьте  сумму перевода, например: 500 рублей",
                    parse_mode="MarkdownV2"
                )  
                await state.set_state(ClientStates.waiting_for_amount)
                await update_last_activity(state, msg)
                return 
    else:
        msg = await message.answer(
            f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
            parse_mode="MarkdownV2"
        )  
        await state.set_state(ClientStates.waiting_for_bank)
        await update_last_activity(state, msg)
        return