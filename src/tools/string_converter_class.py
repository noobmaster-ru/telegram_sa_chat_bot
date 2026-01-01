import re
import secrets
import string
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict
from src.core.config import constants


AMOUNT_PATTERN = re.compile(
    r"(?<!\d[ -])"
    r"\b(\d{1,6}(?:[.,]\d{1,2})?\s?(?:р|руб(?:лей)?|₽|Р|Рублей)?)\b"
    r"(?![ -]?\d)",
    re.IGNORECASE,
)

class StringConverter:
    @staticmethod
    def escape_markdown_v2(text: str) -> str:
        return re.sub(r"([_\[\]()~#+>\-=|{}.!])", r"\\\1", text)
    
    @staticmethod
    def extract_table_id(url: str) -> str | None:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def get_today_date() -> str:
        return datetime.now().strftime("%Y-%m-%d")
    
    @staticmethod
    def convert_phone_to_hash_format(phone_number: str) -> str:
        # 1. Убираем всё, кроме цифр
        digits = re.sub(r'\D', '', phone_number)
        # 2. Если номер начинается с 8 — заменяем на 7
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        return f"#00{digits}"
    
    # 0079876543210 example
    @staticmethod
    def convert_phone_to_superbanking_format(phone_number: str) -> str:
        digits = re.sub(r'\D', '', phone_number)
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        return f"00{digits}"
    
    @staticmethod
    def get_now_str() -> str:
        return str(datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S"))
    

    @staticmethod
    def generate_link_code(length: int = 8) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def _norm(s: str) -> str:
        """
        Нормализует строку для грубого сравнения:
        - нижний регистр
        - ё -> е
        - выкидывает пробелы, дефисы, кавычки и т.п.
        """
        s = s.lower()
        s = s.replace("ё", "е")
        for ch in (" ", "-", "«", "»", "\"", "'", "(", ")", ".", ",", "–", "—"):
            s = s.replace(ch, "")
        return s
    
    @staticmethod
    def parse_amount(text: str) -> Optional[int]:
        """
        Возвращает сумму в рублях как int (без 'р', 'руб', '₽').
        Например:
        'Отправь 1500р' -> 1500
        '1 234,50 руб' -> 1234
        """
        m = AMOUNT_PATTERN.search(text)
        if not m:
            return None

        raw = m.group(1)  # например '1500р' или '1234,50 руб'

        # убираем все буквы и символы валюты, оставляем только цифры, '.', ','
        cleaned = re.sub(r"[^\d.,]", "", raw)  # '1500' или '1234,50'

        if not cleaned:
            return None

        # заменяем запятую на точку
        cleaned = cleaned.replace(",", ".")

        try:
            value = float(cleaned)
        except ValueError:
            return None

        # Superbanking ждёт рубли целым числом – округляем/обрезаем по твоей логике
        return int(value)
