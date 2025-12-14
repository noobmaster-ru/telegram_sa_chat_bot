import re
import secrets
import string
from datetime import datetime
from zoneinfo import ZoneInfo

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
    
    @staticmethod
    def get_now_str() -> str:
        return str(datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S"))
    

    @staticmethod
    def generate_link_code(length: int = 8) -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))
