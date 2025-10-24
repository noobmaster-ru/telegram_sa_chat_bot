from aiogram import Router, F
from aiogram.types import Message
import re
from google_sheets.google_sheets_class import GoogleSheetClass
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from handlers.states.user_flow import UserFlow
from ai_module.open_ai_requests_class import OpenAiRequestClass
router = Router()


# Номер карты: 4 группы по 4 цифры, разделитель пробел или дефис опционален.
card_pattern = r"(\d{4}(?:[ -]?\d{4}){3})"


# Сумма: обязательно суффикс р/руб/рублей, допускаем пробел перед суффиксом
amount_pattern = r"(\d+\s?(?:р|руб|рублей|₽|Р|Рублей))"

# Телефон: количество цифр 9–11, возможно с +7 или 8 в начале
phone_pattern = r"(\+7\d{8,10}|8\d{8,10}|\d{9,11})"

# --- Новый хэндлер для реквизитов:  хотя бы 2 цифры или + или Руб/₽ ---
@router.business_message(StateFilter(UserFlow.waiting_for_requisites))# F.text.regexp(r"(?:(?:.*\d){2,}.*|\+.*|.*(?:руб|₽|рублей).*?)", flags=re.IGNORECASE))
async def handle_requisites_message(
    message: Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    ADMIN_ID_LIST: list,
    state: FSMContext,
    client_gpt_5: OpenAiRequestClass,
    instruction_str: str,
    CHANNEL_USERNAME: str
):
    """
    Ловит сообщения с реквизитами:
    - содержат цифры
    - могут содержать 'руб', '₽', '+', 'Руб', 'рублей'
    """
    telegram_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name or "без full_name"
    text = message.text.strip() if message.text else "(без текста)"

    # тестируем только мы с темой
    if telegram_id in ADMIN_ID_LIST:
        # обновляем время последнего сообщения
        spreadsheet.update_buyer_last_time_message(
            sheet_name=BUYERS_SHEET_NAME,
            telegram_id=telegram_id
        )
        gpt_5_response = client_gpt_5.get_gpt_5_response_requisites(
            new_prompt=text,
            instruction_str=instruction_str,
            CHANNEL_NAME=CHANNEL_USERNAME
        )
        await message.answer(gpt_5_response)
        
        card_match = re.search(card_pattern, text)
        amount_match = re.search(amount_pattern, text)
        phone_match = re.search(phone_pattern, text)
        
        card_number = card_match.group(1) if card_match else ""
        amount = amount_match.group(1) if amount_match else ""
        phone_number = phone_match.group(1) if phone_match else ""
        # # Убираем лишние пробелы и приводим к удобному виду
        # clean_text = re.sub(r"\s+", " ", text)
        # text_only_with_numbers = clean_text.split(" ")

        # list_only_numbers = [elem for elem in text_only_with_numbers if re.search(r'\d', elem)]
        
        await message.answer(f"📩 Получены реквизиты(бот):\nНомер телефона: `{phone_number}`\nНомер карты: `{card_number}`\nСумма: `{amount}`", parse_mode="Markdown")

        if card_number:
            # сохраняем ответ - реквизиты
            spreadsheet.update_buyer_button_status(
                sheet_name=BUYERS_SHEET_NAME,
                telegram_id=telegram_id,
                button_name="requisites",
                value=card_number
            )
        if amount:
            # сохраняем ответ - сумма выплаты
            spreadsheet.update_buyer_button_status(
                sheet_name=BUYERS_SHEET_NAME,
                telegram_id=telegram_id,
                button_name="amount",
                value=amount
            )
        if phone_number:
            # сохраняем ответ - реквизиты
            spreadsheet.update_buyer_button_status(
                sheet_name=BUYERS_SHEET_NAME,
                telegram_id=telegram_id,
                button_name="requisites",
                value=phone_number
            )
        # очищаем состояние, чтобы после этого хэндлера отвечала модель на текстовые сообщения
        await state.clear() 