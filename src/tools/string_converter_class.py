import re
from datetime import datetime

class StringConverter:
    @staticmethod
    def escape_markdown_v2(text: str) -> str:
        return re.sub(r"([_\[\]()~#+\-=|{}.!])", r"\\\1", text)
    
    @staticmethod
    def extract_table_id(url: str) -> str | None:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def get_today_date() -> str:
        return datetime.now().strftime("%Y-%m-%d")