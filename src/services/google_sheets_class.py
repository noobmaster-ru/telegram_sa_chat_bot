import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from gspread_asyncio import AsyncioGspreadClientManager, AsyncioGspreadSpreadsheet
from redis.asyncio import Redis

import logging

class GoogleSheetClass:
    """⚡ Быстрое асинхронное взаимодействие с Google Sheets с кэшами и пакетными апдейтами."""
    def __init__(
        self, 
        service_account_json: str,
        table_url: str, 
        buyers_sheet_name: str,
        redis_client: Redis
    ):
        # Авторизация и получение объекта листа
        self.table_url = table_url
        self.buyers_sheet_name = buyers_sheet_name
        self.service_account_json = service_account_json
        # ✅ Загружаем JSON сразу при инициализации
        with open(self.service_account_json, "r") as f:
            self.service_account_info = json.load(f)

        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # ✅ Создаём Credentials один раз
        self._creds = Credentials.from_service_account_info(
            self.service_account_info, scopes=self.scopes
        )

        # ✅ Передаём функцию, возвращающую эти креды
        self.agcm = AsyncioGspreadClientManager(lambda: self._creds)
        self.client = None
        self.spreadsheet = None
        self.sheet = None

        self.header_row = None 
        self._header_cache = None
        
        # redis
        self.redis = redis_client
        self.redis_key = "user_row_position_in_google_sheets"
    
    async def get_client(self):
        if self.client is None:
            self.client = await self.agcm.authorize()
        return self.client

    async def get_spreadsheet(self) -> AsyncioGspreadSpreadsheet:
        if self.spreadsheet is None:
            client = await self.get_client()
            self.spreadsheet = await client.open_by_url(self.table_url)
        return self.spreadsheet
    
    async def get_sheet(self):
        if self.sheet is None:
            self.sheet = await self.spreadsheet.worksheet(self.buyers_sheet_name)
            self.header_row = await self.sheet.row_values(1)
            self._header_cache = {header: idx + 1 for idx, header in enumerate(self.header_row)}
        return self.sheet 
    
    # === Утилиты ===
    @staticmethod
    def _get_now_str() -> str:
        return str(datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S"))
    
    async def get_user_row(self, telegram_id: int) -> int:
        """Возвращает индекс строки из Redis или ищет в таблице, если в кэше нет."""
        key = f"{self.redis_key}:{telegram_id}"
        row_index = await self.redis.get(key)
        if row_index:
            return int(row_index)

        # ❌ Если нет в Redis — ищем в таблице
        sheet = self.sheet or await self.get_sheet()
        cell = await sheet.find(str(telegram_id))
        row_index = cell.row

        # ✅ Сохраняем в Redis
        await self.redis.set(key, row_index)
        return row_index 
  
    # === Основные операции ===
    async def add_new_buyer(self, username: str, telegram_id: int, nm_id: int) -> None:
        sheet = self.sheet or await self.get_sheet()
        new_row = [''] * len(self._header_cache)
        
        now = self._get_now_str()
        user_link = f"https://t.me/{username}" if username != "без username" else "—"

        new_row[0] = user_link # ссылка на ник
        new_row[1] = str(telegram_id) # telegram_Id
        new_row[2] = now # дата первого сообщения
        new_row[3] = now # дата последнего сообщения
        new_row[4] = str(nm_id) # артикул

        await sheet.append_row(new_row)  

        # После добавления — найти строку юзера в гугл-таблице и сохранить в Redis в кэш 
        cell = await sheet.find(str(telegram_id))
        await self.redis.set(f"{self.redis_key}:{telegram_id}", cell.row)
    
    # === Быстрое обновление статусов ===
    async def update_buyer_last_time_message(self, telegram_id: int) -> None:
        sheet = self.sheet or await self.get_sheet()
        row_index = await self.get_user_row(telegram_id)
        col_index = self._header_cache.get('Дата последнего сообщения')
        await sheet.update_cell(row_index, col_index, self._get_now_str())


    async def update_buyer_button_status(
        self,
        telegram_id: int,
        button_name: str,
        value: str,
    ) -> None:
        sheet = self.sheet or await self.get_sheet()
        # Маппинг логических имён на реальные заголовки
        button_to_column = {
            "agree": "Условия", 
            "subscribe": "Подписка на канал",
            "order": "Заказ сделан",
            "receive": "Заказ получен",
            "feedback": "Отзыв оставлен",
            "shk": "ШК разрезаны", 
            "requisites": "Номер карты", 
            "phone_number": "Номер телефона", 
            "bank": "Банк", 
            "amount": "Сумма,₽",
            "photo_order": "Скрин заказа",
            "photo_shk": "Фото разрезанных ШК"
        }
        column_name = button_to_column.get(button_name)
        row_index = await self.get_user_row(telegram_id)
        col_index = self._header_cache[column_name]
        await sheet.update_cell(row_index, col_index, value)
   
    async def write_requisites_into_google_sheets(
        self,
        telegram_id: int,
        card_number: str,
        phone_number: str,
        bank: str,
        amount: str,
    ) -> None:
        """Обновляет реквизиты (карта, сумма, телефон, банк) одной операцией."""
        sheet = self.sheet or await self.get_sheet()
        row_index = await self.get_user_row(telegram_id)

        # Маппинг из логических имен в заголовки
        fields = {
            "Номер карты": card_number or '-',
            "Номер телефона": phone_number or '-',
            "Банк": bank or '-',
            "Сумма,₽": amount or '-',
        }

        # Подготавливаем все апдейты для batch_update
        updates = []
        for column_name, value in fields.items():
            col_index = self._header_cache[column_name]
            # Конвертация номера столбца в букву (например 14 → N)
            col_letter = chr(64 + col_index)
            cell_range = f"{col_letter}{row_index}"
            updates.append({"range": cell_range, "values": [[value]]})
        logging.info(f"  user: {telegram_id}, writes requisites into GoogleSheet: {card_number}, {phone_number}, {bank}, {amount}")
        # Один батч-запрос к API
        await sheet.batch_update(updates)
    
    # === Other methods ===
    async def get_nm_id(self, sheet_articles: str) -> str:
        sheet = await (await self.get_spreadsheet()).worksheet(sheet_articles)
        nm_id_cell = await sheet.acell("A2")
        return nm_id_cell.value

    async def get_instruction(self, sheet_instruction: str, nm_id: str) -> str:
        sheet = await (await self.get_spreadsheet()).worksheet(sheet_instruction)
        instruction_cell = await sheet.acell("A1")
        instruction_str = instruction_cell.value

        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }

        today = datetime.now(ZoneInfo("Europe/Moscow"))
        today_date = f"{today.day}_{months[today.month]}"

        instruction_str = (
            instruction_str.replace("{", "{{").replace("}", "}}")
            .replace("{{nm_id}}", "{nm_id}")
            .replace("{{today_date}}", "{today_date}")
        )

        filled = instruction_str.format(nm_id=nm_id, today_date=today_date)
        return re.sub(r"([_\[\]()~#+\-=|{}.!])", r"\\\1", filled)