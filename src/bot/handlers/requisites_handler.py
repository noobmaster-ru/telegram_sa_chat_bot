import re
import logging
import asyncio

from aiogram import Router, F
from aiogram.types import Message,  CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.states.user_flow import UserFlow

from src.services.open_ai_requests_class import OpenAiRequestClass
from src.services.google_sheets_class import GoogleSheetClass
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.utils.last_activity import update_last_activity

router = Router()

# --- Регулярки ---
# Номер карты: 16 подряд цифр или 4 группы по 4 с пробелом/дефисом
card_pattern = r"\b(?:\d{16}|\d{4}(?:[ -]\d{4}){3})\b"

# Сумма с "р", "руб", "₽" иил
# amount_pattern = r"\b(\d{1,6}(?:[.,]\d{1,2})?\s?(?:р|руб|рублей|₽|Р|Рублей)?)\b"
amount_pattern = (
    r"(?<!\d[ -])"  # перед числом не должно быть цифры + пробела/дефиса
    r"\b(\d{1,6}(?:[.,]\d{1,2})?\s?(?:р|руб(?:лей)?|₽|Р|Рублей)?)\b"
    r"(?![ -]?\d)"  # после числа не должно идти цифра через пробел/дефис
)

# Телефон в формате +7910... или 8910... или 7910...
phone_pattern = r"\b(?:\+7|8|7)[\s\-()]?\d{3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}\b"

# Название банка
bank_pattern = (
    r"(?<!\w)("
    r"сбер(?:банк)?|тинькофф|тинькоф|тиньков|т[-\s]?банк|альфа(?:банк)?|"
    r"втб|газпромбанк|райф+айзен|росбанк|открытие|почтабанк|отп|совкомбанк|мтс(?:банк)?|яндекс(?:банк)?"
    r")(?!\w)"
)


# --- Новый хэндлер для реквизитов: ---
@router.business_message(StateFilter(UserFlow.waiting_for_requisites))
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
    await update_last_activity(state)
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    telegram_id = message.from_user.id
    text = message.text.strip()

    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    nm_id_amount = user_data.get("nm_id_amount")
    
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )


    # --- Поиск данных ---
    cards = re.findall(card_pattern, text)
    amounts = re.findall(amount_pattern, text, flags=re.IGNORECASE)
    phones = re.findall(phone_pattern, text)
    bank_match = re.search(bank_pattern, text, flags=re.IGNORECASE)
    
    # Запись в переменные (берём первое найденное или None)
    card_number = cards[0] if cards else None
    amount = amounts[0] if amounts else None
    phone_number = phones[0] if phones else None
    bank = bank_match.group(0).capitalize() if bank_match else None



    # --- Сохраняем найденное в FSM ---
    data = await state.get_data()
    # logging.info(data) - {} выводит
    if card_number:
        data["card_number"] = re.sub(r"[ -]", "", card_number)
    if amount:
        data["amount"] = amount
    if phone_number:
        data["phone_number"] = re.sub(r"^\+?8", "8", phone_number)  # нормализуем формат
    if bank:
        data["bank"] = bank
    await state.update_data(**data)
    
    
    # --- Проверяем, всё ли есть ---
    card_number = data.get("card_number")
    phone = data.get("phone_number")
    amt = data.get("amount")
    bank_name = data.get("bank")
    logging.info(f"  user: {telegram_id} gave requisites: card_number = {card_number} , phone = {phone}, amount = {amt}, bank = {bank_name}")
    
    # если банк, карта, телефон и сумма
    if bank_name and card_number and  phone_number and amt:
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер карты: `{card_number}`\n"
            f"Номер телефона: `{phone}`\n"
            f"Банк: `{bank}`\n"
            f"Сумма: `{amt}`\n\n"
            f"Реквизиты заполнены верно?",
            parse_mode="Markdown",
            reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
        )
        await state.set_state(UserFlow.confirming_requisites)
        return
    
    # если только номер телефона
    if not bank_name and not card_number and phone_number and not amt:
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер телефона: `{phone}`\n\n"
            f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
            parse_mode="Markdown"
        )
        await state.set_state(UserFlow.waiting_for_amount)
        return
    
    # если только банк
    if bank_name and not card_number and not phone_number and not amt:
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Банк: `{bank}`\n\n"
            f"💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона или номер банковской карты.",
            parse_mode="Markdown"
        )
        await state.set_state(UserFlow.waiting_for_card_or_phone_number)
        return
    
    # если только номер карты
    if not bank_name and card_number and not phone_number and not amt:
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер карты: `{card_number}`\n\n"
            f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
            parse_mode="Markdown"
        )
        await state.set_state(UserFlow.waiting_for_amount)
        return
    
    # если только сумма
    if not bank_name and not card_number and not phone_number and amt:
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Сумма: `{amt}`\n\n"
            f"💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона или номер банковской карты.",
            parse_mode="Markdown"
        )
        await state.set_state(UserFlow.waiting_for_card_or_phone_number)
        return
    
    # если карта , номер телефона и банк, но нет суммы оплаты
    if phone and card_number and bank_name and not amt:
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер телефона: `{phone}`\n"
            f"Номер карты: `{card_number}`\n"
            f"Банк: `{bank}`\n\n"
            f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
            parse_mode="Markdown"
        )
        await state.set_state(UserFlow.waiting_for_amount)
        return
    
    # если только номер карты или телефона
    if (phone or card_number) and not bank_name and not amt:
        if phone:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="Markdown"
            )
        if card_number:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="Markdown"
            )  
        await state.set_state(UserFlow.waiting_for_amount)
        return
    

    # если только cумма и банк
    if not phone and not card_number and bank_name and amt:
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Банк: `{bank}`\n"
            f"Сумма: `{amt}`\n\n"
           f"💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона или номер банковской карты.",
            parse_mode="Markdown"
        )  
        await state.set_state(UserFlow.waiting_for_card_or_phone_number)
        return
    
    # если нет суммы платежа
    if bank_name and (phone or card_number) and not amt:
        if phone and card_number:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number}`\n"
                f"Номер телефона: `{phone}`\n"
                f"Банк: `{bank}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="Markdown"
            )
        elif card_number:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number}`\n"
                f"Банк: `{bank}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="Markdown"
            ) 
        else:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n"
                f"Банк: `{bank}`\n\n"
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="Markdown"
            )
        await state.set_state(UserFlow.waiting_for_amount)
        return
    
    # если нет банка 
    if not bank_name and (phone or card_number) and amt:
        if phone and card_number:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n"
                f"Номер карты: `{card_number}`\n"
                f"Сумма: `{amt}`\n\n"
                f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
                parse_mode="Markdown"
            )
        elif card_number:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number or ''}`\n"
                f"Сумма: `{amt or ''}`\n\n"
                f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
                parse_mode="Markdown"
            ) 
        else:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone}`\n"
                f"Сумма: `{amt}`\n\n"
                f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
                parse_mode="Markdown"
            ) 
        await state.set_state(UserFlow.waiting_for_bank)
        return
    
    # --- Если всё есть(телефон, банк , сумма), показываем кнопки подтверждения ---
    if all(k in data for k in ("phone_number", "amount", "bank")):
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер телефона: `{data['phone_number']}`\n"
            f"Банк: {data['bank']}\n"
            f"Сумма: `{data['amount']}`\n\n"
            f"Реквизиты заполнены верно?",
            parse_mode="Markdown",
            reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
        )
        await state.set_state(UserFlow.confirming_requisites)
        return 
    
    # --- Если всё есть(карта, банк , сумма), показываем кнопки подтверждения ---
    if all(k in data for k in ("card_number", "amount", "bank")):
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер карты: {data['card_number']}\n"
            f"Банк: {data['bank']}\n"
            f"Сумма: `{data['amount']}`\n\n"
            f"Реквизиты заполнены верно?",
            parse_mode="Markdown",
            reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
        )
        await state.set_state(UserFlow.confirming_requisites)
        return 
    
    # если юзер мега тупой и ввел какой-то текст, то загоняем текст в модель
    # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
    await state.set_state('generating')
    gpt5_response_text = await client_gpt_5.create_gpt_5_response_requisites(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_requisites)
    await message.answer(gpt5_response_text)

@router.business_message(StateFilter(UserFlow.waiting_for_amount))
async def handle_amount(
    message: Message, 
    state: FSMContext,
    spreadsheet: GoogleSheetClass
):
    await update_last_activity(state)
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    text = message.text.strip()
    telegram_id = message.from_user.id
    amounts = re.findall(amount_pattern, text, flags=re.IGNORECASE)
    amount = amounts[0] if amounts else None
    await state.update_data(amount=amount)

    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )  
    data = await state.get_data()
    if data.get('bank'):
        if data.get('card_number'):
            if data.get('phone_number'):
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return
            else:
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return
        elif data.get('phone_number'):
            if data.get('card_number'):
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return
            else:
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return
    else:
        await message.answer(
            f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
            parse_mode="Markdown"
        )  
        await state.set_state(UserFlow.waiting_for_bank)


@router.business_message(StateFilter(UserFlow.waiting_for_card_or_phone_number))
async def handle_card_or_phone_number(
    message: Message, 
    state: FSMContext,
    spreadsheet: GoogleSheetClass
):
    await update_last_activity(state)
    text = message.text.strip()
    telegram_id = message.from_user.id
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    
    # --- Поиск данных ---
    cards = re.findall(card_pattern, text)
    phones = re.findall(phone_pattern, text)
    
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
    if data.get('bank'):
        if data.get('card_number'):
            if data.get('amount'):
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер карты: `{data.get('card_number', '')}`\n"
                    f"Банк: {data.get('bank', '')}\n"
                    f"Сумма: `{data.get('amount', '')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return 
            else:
                await message.answer(
                    f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                    parse_mode="Markdown"
                )  
                await state.set_state(UserFlow.waiting_for_amount)
                return 
        if data.get('phone_number'):
            if data.get('amount'):
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number', '')}`\n"
                    f"Банк: {data.get('bank', '')}\n"
                    f"Сумма: `{data.get('amount', '')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return 
            else:
                await message.answer(
                    f"💬 Пожалуйста, отправьте  сумму перевода, например: 500 рублей",
                    parse_mode="Markdown"
                )  
                await state.set_state(UserFlow.waiting_for_amount)
                return 
    else:
        await message.answer(
            f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
            parse_mode="Markdown"
        )  
        await state.set_state(UserFlow.waiting_for_bank)
        return

@router.business_message(StateFilter(UserFlow.waiting_for_bank))
async def handle_bank_name(
    message: Message, 
    state: FSMContext,
    spreadsheet: GoogleSheetClass
):
    await update_last_activity(state)
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    text = message.text.strip()
    telegram_id = message.from_user.id
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    bank_match = re.search(bank_pattern, text, flags=re.IGNORECASE)
    bank = bank_match.group(0).capitalize() if bank_match else None
    await state.update_data(bank=bank)

    data = await state.get_data()
    if data.get("amount"):
        if data.get('card_number'):
            if data.get('phone_number'):
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return
            else:
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return
        if data.get('phone_number'):
            if data.get('card_number'):
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Номер карты: `{data.get('card_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return 
            else:
                await message.answer(
                    f"📩 Получены реквизиты:\n"
                    f"Номер телефона: `{data.get('phone_number')}`\n"
                    f"Банк: {data.get('bank')}\n"
                    f"Сумма: `{data.get('amount')}`\n\n"
                    f"Реквизиты заполнены верно?",
                    parse_mode="Markdown",
                    reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
                )
                await state.set_state(UserFlow.confirming_requisites)
                return
    else:
        await message.answer(
                f"💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
                parse_mode="Markdown"
            )
        await state.set_state(UserFlow.waiting_for_amount)
        return



@router.callback_query(StateFilter(UserFlow.confirming_requisites), F.data == "confirm_requisites_no")
async def confirm_requisites_no(
    callback: CallbackQuery, 
    state: FSMContext
):
    """
    Пользователь указал, что реквизиты неверные — начинаем ввод заново.
    """
    await update_last_activity(state)
    await callback.message.bot(
        ReadBusinessMessage(
            business_connection_id=callback.message.business_connection_id,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    )
    await callback.answer()
    
    # Получаем текущее состояние FSM
    user_data = await state.get_data()
    
    # Удаленияем определенного ключа (например, 'username') из словаря Python
    if 'bank' in user_data:
        del user_data['bank']
    if 'amount' in user_data:
        del user_data['amount']
    if 'phone_number' in user_data:
        del user_data['phone_number']
    if 'card_number' in user_data:
        del user_data['card_number']
        
    # Обновление данных в FSMContext
    await state.set_data(user_data)
    
    # ставим новое состояние
    await state.set_state(UserFlow.waiting_for_requisites)
    await callback.message.edit_text(
        "❌ Хорошо, давайте попробуем ещё раз.\n"
        "Отправьте номер телефона, сумму для оплаты , название банка и (если есть) номер карты одним сообщением."
    )

@router.callback_query(StateFilter(UserFlow.confirming_requisites), F.data == "confirm_requisites_yes")
async def confirm_requisites_yes(
    callback: CallbackQuery, 
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
):
    await update_last_activity(state)
    await callback.answer()
    """
    Пользователь указал, что реквизиты верные — сохраняем их в гугл таблицу и очищаем состояние.
    """
    await callback.message.bot(
        ReadBusinessMessage(
            business_connection_id=callback.message.business_connection_id,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    )
    data = await state.get_data()
    telegram_id = callback.from_user.id


    # записываем данные в гугл-таблицу и однвременно обновим последнее время записи
    await spreadsheet.write_requisites_into_google_sheets_and_update_last_time_message(
        telegram_id=telegram_id,
        card_number=data.get('card_number', '-'),
        phone_number=data.get('phone_number','-'),
        bank=data.get('bank','-'),
        amount=data.get('amount','-'),
    )

    await state.set_state(UserFlow.continue_dialog)
    await callback.message.edit_text(
        f"📩 Реквизиты записаны:\n"
        f"Номер карты: `{data.get('card_number', '-')}`\n"
        f"Номер телефона: `{data.get('phone_number', '-')}`\n"
        f"Банк: {data.get('bank', '-')}\n"
        f"Сумма: `{data.get('amount', '-')}`\n\n"
        f"Ожидайте выплату в ближайшее время, спасибо ☺️",
        parse_mode="Markdown"
    )
    # удаляем данные из состояния и из redis (но можно и оставить так-то)
    # await state.set_data({})