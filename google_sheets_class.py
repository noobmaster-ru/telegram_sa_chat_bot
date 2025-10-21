from gspread import service_account
from datetime import datetime
from zoneinfo import ZoneInfo
import re

class GoogleSheetClass():
    def __init__(self, service_account_json: str, table_url: str):
        self.client = service_account(filename=service_account_json)
        self.spreadsheet = self.client.open_by_url(table_url)
    
    def get_nm_id(self, sheet_articles: str) -> int:
        sheet = self.spreadsheet.worksheet(sheet_articles)
        nm_id = sheet.acell('A2').value
        return nm_id
    
    def get_instruction(self, sheet_instruction: str, nm_id: str) -> str:
        sheet = self.spreadsheet.worksheet(sheet_instruction)
        instruction_str = sheet.acell('A1').value
        # форматируем красиво и чтобы телеграм не ругался
        filled_instruction = instruction_str.format(nm_id=nm_id)
        return re.sub(r'([_\[\]()~#+\-=|{}.!])', r'\\\1', filled_instruction)
    
    def add_new_buyer(
        self,
        sheet_name: str,
        username: str,
        nm_id: str,
        status: str = "None", # потом можно обновлять статус отдельной функцией (заказал, получил, оставил отзыв)
        requisites: str = "None",
        paid: str = "None"
    ):
        """
        Добавляет нового пользователя в таблицу.
        Формат таблицы:
        Ссылка на ник | Дата первого | Дата последнего | Артикул | Статус | Реквизиты | Выплата произведена
        """
        sheet = self.spreadsheet.worksheet(sheet_name)
        # all_rows = sheet.get_all_values()  # все строки листа
        now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")
        user_link = f"https://t.me/{username}" if username != "без username" else "—"
        
        # добавляем новую строку с данными пользователя 
        new_row = [user_link, now, now, nm_id, status, requisites, paid]
        sheet.append_row(new_row)

    def update_buyer_last_time_message(
        self,
        sheet_name: str,
        username: str
    ) -> None:
        """
        Обновляет дату последнего сообщения.
        Формат таблицы:
        Ссылка на ник | Дата первого | Дата последнего | Артикул | Статус | Реквизиты | Выплата произведена
        """
        sheet = self.spreadsheet.worksheet(sheet_name)
        all_rows = sheet.get_all_values()  # все строки листа
        now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")
        user_link = f"https://t.me/{username}" if username != "без username" else "—"

        # если таблица не пуста, ищем пользователя начиная со 2-й строки
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > 0 and row[0] == user_link:
                # обновляем только дату последнего сообщения
                sheet.update_cell(i, 3, now)
                return