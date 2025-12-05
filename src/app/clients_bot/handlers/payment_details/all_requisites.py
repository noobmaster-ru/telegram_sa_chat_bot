import re
import logging

from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage


from src.app.bot.states.client import ClientStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.utils.last_activity import update_last_activity
from src.infrastructure.apis.open_ai_requests_class import OpenAiRequestClass
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

# --- Новый хэндлер для реквизитов: ---
@router.business_message(StateFilter(ClientStates.waiting_for_requisites))
async def handle_requisites_message(
    message: Message,
    spreadsheet: GoogleSheetClass,
    state: FSMContext,
    client_gpt_5: OpenAiRequestClass
):
    """
    Обрабатывает сообщение с реквизитами:
    — ищет телефон, сумму, карту, банк
    — если чего-то не хватает — просит дополнить
    — если всё найдено — предлагает подтвердить
    """
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    user_data = await state.get_data()
    telegram_id = message.from_user.id
    text = message.text.strip()
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    

    nm_id_name = user_data.get("nm_id_name")
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )


    # --- Поиск данных ---
    cards = re.findall(constants.card_pattern, text)
    amounts = re.findall(constants.amount_pattern, text, flags=re.IGNORECASE)
    phones = re.findall(constants.phone_pattern, text)
    bank_match = re.search(constants.bank_pattern, text, flags=re.IGNORECASE)
    
    # Запись в переменные (берём первое найденное или None)
    card_number = cards[0] if cards else None
    amount = amounts[0] if amounts else None
    phone_number = phones[0] if phones else None
    # logging.info(phone_number)
    bank = bank_match.group(0).capitalize() if bank_match else None



    # --- Сохраняем найденное в FSM ---
    data = await state.get_data()
    # logging.info(data) - {} выводит
    if card_number:
        data["card_number"] = re.sub(r"[ -]", "", card_number)
    if amount:
        data["amount"] = amount
    if phone_number:
        data["phone_number"] = phone_number  # нормализуем формат
    if bank:
        data["bank"] = bank
    await state.update_data(**data)
    
    
    # --- Проверяем, всё ли есть ---
    card_number = data.get("card_number")
    phone = data.get("phone_number")
    amt = data.get("amount")
    bank_name = data.get("bank")
    logging.info(f"  user: {telegram_id} gave requisites: card_number = {card_number} , phone = {phone}, amount = {amt}, bank = {bank_name}")
    
    # ============== MAIN FLOW =============
    # если только номер телефона
    if phone_number and not bank_name and not card_number and not amt:
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер телефона: `{phone}`\n\n"
            f"💬 Пожалуйста, отправьте сумму перевода, например: *500*",
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_amount)
        await update_last_activity(state, msg)
        return
    # ============== MAIN FLOW =============    

    # если банк, карта, телефон и сумма
    if bank_name and card_number and  phone_number and amt:
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер карты: `{card_number}`\n"
            f"Номер телефона: `{phone}`\n"
            f"Банк: `{bank}`\n"
            f"Сумма: `{amt}`\n\n"
            f"Реквизиты заполнены верно?",
            parse_mode="MarkdownV2",
            reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
        )
        await state.set_state(ClientStates.confirming_requisites)
        await update_last_activity(state, msg)
        return
    
    
    # если только банк
    if bank_name and not card_number and not phone_number and not amt:
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Банк: `{bank}`\n\n"
            f"💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона или номер банковской карты.",
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_card_or_phone_number)
        await update_last_activity(state, msg)
        return
    
    # если только номер карты
    if not bank_name and card_number and not phone_number and not amt:
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер карты: `{card_number}`\n\n"
            f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_amount)
        await update_last_activity(state, msg)
        return
    
    # если только сумма
    if not bank_name and not card_number and not phone_number and amt:
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Сумма: `{amt}`\n\n"
            f"💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона или номер банковской карты.",
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_card_or_phone_number)
        await update_last_activity(state, msg)
        return
    
    # если карта , номер телефона и банк, но нет суммы оплаты
    if phone and card_number and bank_name and not amt:
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер телефона: `{phone}`\n"
            f"Номер карты: `{card_number}`\n"
            f"Банк: `{bank}`\n\n"
            f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_amount)
        await update_last_activity(state, msg)
        return
    
    # если только номер карты или телефона
    if (phone or card_number) and not bank_name and not amt:
        msg = None
        if phone:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="MarkdownV2"
            )
        if card_number:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="MarkdownV2"
            )  
        await state.set_state(ClientStates.waiting_for_amount)
        await update_last_activity(state, msg)
        return
    

    # если только cумма и банк
    if not phone and not card_number and bank_name and amt:
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Банк: `{bank}`\n"
            f"Сумма: `{amt}`\n\n"
           f"💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона или номер банковской карты.",
            parse_mode="MarkdownV2"
        )  
        await state.set_state(ClientStates.waiting_for_card_or_phone_number)
        await update_last_activity(state, msg)
        return
    
    # если нет суммы платежа
    if bank_name and (phone or card_number) and not amt:
        msg = None
        if phone and card_number:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number}`\n"
                f"Номер телефона: `{phone}`\n"
                f"Банк: `{bank}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="MarkdownV2"
            )
        elif card_number:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number}`\n"
                f"Банк: `{bank}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="MarkdownV2"
            ) 
        else:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n"
                f"Банк: `{bank}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="MarkdownV2"
            )
        await state.set_state(ClientStates.waiting_for_amount)
        await update_last_activity(state, msg)
        return
    
    # если нет банка 
    if not bank_name and (phone or card_number) and amt:
        msg = None
        if phone and card_number:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n"
                f"Номер карты: `{card_number}`\n"
                f"Сумма: `{amt}`\n\n"
                f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
                parse_mode="MarkdownV2"
            )
        elif card_number:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number or ''}`\n"
                f"Сумма: `{amt or ''}`\n\n"
                f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
                parse_mode="MarkdownV2"
            ) 
        else:
            msg = await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n"
                f"Сумма: `{amt}`\n\n"
                f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
                parse_mode="MarkdownV2"
            ) 
        await state.set_state(ClientStates.waiting_for_bank)
        await update_last_activity(state, msg)
        return
    
    # --- Если всё есть(телефон, банк , сумма), показываем кнопки подтверждения ---
    if all(k in data for k in ("phone_number", "amount", "bank")):
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер телефона: `{data['phone_number']}`\n"
            f"Банк: {data['bank']}\n"
            f"Сумма: `{data['amount']}`\n\n"
            f"Реквизиты заполнены верно?",
            parse_mode="MarkdownV2",
            reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
        )
        await state.set_state(ClientStates.confirming_requisites)
        await update_last_activity(state, msg)
        return 
    
    # --- Если всё есть(карта, банк , сумма), показываем кнопки подтверждения ---
    if all(k in data for k in ("card_number", "amount", "bank")):
        msg = await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер карты: {data['card_number']}\n"
            f"Банк: {data['bank']}\n"
            f"Сумма: `{data['amount']}`\n\n"
            f"Реквизиты заполнены верно?",
            parse_mode="MarkdownV2",
            reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
        )
        await state.set_state(ClientStates.confirming_requisites)
        await update_last_activity(state, msg)
        return 
    
    # если юзер мега тупой и ввел какой-то текст, то загоняем текст в модель
    # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    gpt5_response_text = await client_gpt_5.create_gpt_5_response_requisites(
        new_prompt=text,
        product_title=nm_id_name
    )
    await state.set_state(ClientStates.waiting_for_requisites)
    await message.answer(gpt5_response_text)
