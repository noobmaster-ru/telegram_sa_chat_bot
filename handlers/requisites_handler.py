from aiogram import Router, F
from aiogram.types import Message
import re
from google_sheets.google_sheets_class import GoogleSheetClass

router = Router()


# Номер карты: 4 группы по 4 цифры, разделитель пробел или дефис опционален.
card_pattern = r"(\d{4}(?:[ -]?\d{4}){3})"


# Сумма: обязательно суффикс р/руб/рублей, допускаем пробел перед суффиксом
amount_pattern = r"(\d+\s?(?:р|руб|рублей|₽|Р|Рублей))"

# Телефон: количество цифр 9–11, возможно с +7 или 8 в начале
phone_pattern = r"(\+7\d{8,10}|8\d{8,10}|\d{9,11})"

# --- Новый хэндлер для реквизитов:  хотя бы 2 цифры или + или Руб/₽ ---
@router.business_message(
    F.text.regexp(r"(?:(?:.*\d){2,}.*|\+.*|.*(?:руб|₽).*?)", flags=re.IGNORECASE)
)
async def handle_requisites_message(
    message: Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    ADMIN_ID_LIST: list
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
            username=username
        )
        
        card_match = re.search(card_pattern, text)
        amount_match = re.search(amount_pattern, text)
        phone_match = re.search(phone_pattern, text)
        
        card_number = card_match.group(1) if card_match else None
        amount = amount_match.group(1) if amount_match else None
        phone_number = phone_match.group(1) if phone_match else None
        # # Убираем лишние пробелы и приводим к удобному виду
        # clean_text = re.sub(r"\s+", " ", text)
        # text_only_with_numbers = clean_text.split(" ")

        # list_only_numbers = [elem for elem in text_only_with_numbers if re.search(r'\d', elem)]
        await message.answer(f"📩 Получены реквизиты:\nНомер телефона: `{phone_number}`\nНомер карты: `{card_number}`\nСумма: `{amount}`", parse_mode="Markdown")

        if card_number:
            # сохраняем ответ - реквизиты
            spreadsheet.update_buyer_button_status(
                sheet_name=BUYERS_SHEET_NAME,
                username=username,
                button_name="requisites",
                value=card_number
            )
        if amount:
            # сохраняем ответ - сумма выплаты
            spreadsheet.update_buyer_button_status(
                sheet_name=BUYERS_SHEET_NAME,
                username=username,
                button_name="amount",
                value=amount
            )
        if phone_number:
            # сохраняем ответ - реквизиты
            spreadsheet.update_buyer_button_status(
                sheet_name=BUYERS_SHEET_NAME,
                username=username,
                button_name="requisites",
                value=phone_number
            )