import re
import logging

from aiogram import Router, F
from aiogram.types import Message,  CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from src.bot.states.user_flow import UserFlow

from src.ai_module.open_ai_requests_class import OpenAiRequestClass
from src.google_sheets.google_sheets_class import GoogleSheetClass
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard

router = Router()

# --- Регулярки ---
# Номер карты: 16 подряд цифр или 4 группы по 4 с пробелом/дефисом
card_pattern = r"\b(?:\d{16}|\d{4}(?:[ -]\d{4}){3})\b"

# Сумма с "р", "руб", "₽"
amount_pattern = r"(\d+\s?(?:р|руб|рублей|₽|Р|Рублей))"

# Телефон в формате +7910... или 8910... или 7910...
phone_pattern = r"\b(?:\+7\d{10}|8\d{10}|7\d{10})\b"

# Название банка
bank_pattern = (
    r"\b("
    r"сбер(?:банк)?|тинькофф|т[-\s]?банк|альфа(?:банк)?|"
    r"втб|газпромбанк|райф+айзен|росбанк|открытие|почтабанк|совкомбанк"
    r")\b"
)


# --- Новый хэндлер для реквизитов: ---
@router.business_message(StateFilter(UserFlow.waiting_for_requisites))
async def handle_requisites_message(
    message: Message,
    spreadsheet: GoogleSheetClass,
    ADMIN_ID_LIST: list,
    state: FSMContext,
    client_gpt_5: OpenAiRequestClass
):
    """
    Обрабатывает сообщение с реквизитами:
    — ищет телефон, сумму, карту, банк
    — если чего-то не хватает — просит дополнить
    — если всё найдено — предлагает подтвердить
    """
    
    telegram_id = message.from_user.id
    # тестируем только мы с темой
    if telegram_id not in ADMIN_ID_LIST:
        return

    text = message.text.strip() if message.text else "(без текста)"

    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(telegram_id=telegram_id)

    # !!! загоняем в ии текст с реквизитами, чтобы он выделил четко карту/телефон/сумму!!!
    # gpt_5_response = await client_gpt_5.get_gpt_5_response_requisites(new_prompt=text)        
    

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
        data["phone_number"] = re.sub(r"^\+?8", "7", phone_number)  # нормализуем формат
    if bank:
        data["bank"] = bank
    await state.update_data(**data)
    
    
    # --- Проверяем, всё ли есть ---
    card_number = data.get("card_number")
    phone = data.get("phone_number")
    amt = data.get("amount")
    bank_name = data.get("bank")
    
    if not bank_name and (phone or card_number) and amt:
        if phone:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер телефона: `{phone or ''}`\n"
                f"Банк: \n"
                f"Сумма: `{amt or ''}`\n\n"
                f"💬 Пожалуйста, отправьте название банка (например: *Сбербанк*, *Т-банк*)",
                parse_mode="Markdown"
            )
        if card_number:
            await message.answer(
                f"📩 Получены реквизиты:\n"
                f"Номер карты: `{card_number or ''}`\n"
                f"Банк: \n"
                f"Сумма: `{amt or ''}`\n\n"
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



@router.business_message(StateFilter(UserFlow.waiting_for_bank))
async def handle_bank_name(message: Message, state: FSMContext):
    bank = message.text.strip().title()
    await state.update_data(bank=bank)

    data = await state.get_data()

    if data.get('card_number'):
        await message.answer(
            f"📩 Получены реквизиты:\n"
            f"Номер карты: `{data.get('card_number', '')}`\n"
            f"Банк: {data.get('bank', '')}\n"
            f"Сумма: `{data.get('amount', '')}`\n\n"
            f"Реквизиты заполнены верно?",
            parse_mode="Markdown",
            reply_markup=get_yes_no_keyboard("confirm_requisites", "верно")
        )
    if data.get('phone_number'):
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




@router.callback_query(StateFilter(UserFlow.confirming_requisites), F.data == "confirm_requisites_no")
async def confirm_requisites_no(callback: CallbackQuery, state: FSMContext):
    """
    Пользователь указал, что реквизиты неверные — начинаем ввод заново.
    """
    await state.clear()
    await state.set_state(UserFlow.waiting_for_requisites)

    await callback.message.edit_text(
        "❌ Хорошо, давайте попробуем ещё раз.\n"
        "Отправьте номер телефона, сумму и (если есть) номер карты одним сообщением."
    )


@router.callback_query(StateFilter(UserFlow.confirming_requisites), F.data == "confirm_requisites_yes")
async def confirm_requisites_yes(
    callback: CallbackQuery, 
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
):
    """
    Пользователь указал, что реквизиты верные — сохраняем их в гугл таблицу и очищаем состояние.
    """
    data = await state.get_data()
    telegram_id = callback.from_user.id

    # сохраняем  реквизиты карты в гугл-таблицу 
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
        button_name="requisites",
        value=data.get('card_number', '-')
    )

    # сохраняем сумму выплаты в гугл-таблицу
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
        button_name="amount",
        value=data.get('amount', '-')
    )

    # сохраняем номер телефона в гугл-таблицу
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
        button_name="phone_number",
        value=data.get('phone_number', '-')
    )

    # сохраняем банк в гугл-таблицу
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
        button_name="bank",
        value=data.get('bank', '-')
    )
    await state.clear()
    await callback.message.edit_text(
        f"📩 Реквизиты записаны:\n"
        f"Номер телефона: `{data.get('phone_number', '')}`\n"
        f"Банк: {data.get('bank', '')}\n"
        f"Сумма: `{data.get('amount', '')}`\n\n"
        f"Ожидайте выплату в ближайшее время, спасибо ☺️",
        parse_mode="Markdown"
    )