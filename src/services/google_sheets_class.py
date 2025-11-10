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
        redis_client: Redis,
        REDIS_KEY_USER_ROW_POSITION_STRING: str,
        REDIS_KEY_NM_IDS_ORDERED_LIST: str
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

        # первая строка - названия столбцов
        self.header_row = None 
        self._header_cache = None
        
        # названия столбцов: "Последнее сообщение", "Последнее нажатие на кнопку"
        self.last_message_column_name = None
        self.last_tap_column_name = None
        
        # redis
        self.redis = redis_client
        self.REDIS_KEY_USER_ROW_POSITION_STRING = REDIS_KEY_USER_ROW_POSITION_STRING
        self.REDIS_KEY_NM_IDS_ORDERED_LIST = REDIS_KEY_NM_IDS_ORDERED_LIST
    
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
            # запишем в класс названия столбцов некоторых, чтобы облечить прод
            self.last_message_column_name = self.header_row[4]
            self.last_tap_column_name = self.header_row[5]
            self._header_cache = {header: idx + 1 for idx, header in enumerate(self.header_row)}
        return self.sheet 
    
    # === Утилиты ===
    @staticmethod
    def _get_now_str() -> str:
        return str(datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S"))
    
    async def get_user_row(self, telegram_id: int) -> int:
        """Возвращает индекс строки из Redis или ищет в таблице, если в кэше нет."""
        key = f"{self.REDIS_KEY_USER_ROW_POSITION_STRING}:{telegram_id}"
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
    async def add_new_buyer(self, username: str, full_name: str, telegram_id: int, nm_id: int) -> None:
        sheet = self.sheet or await self.get_sheet()
        new_row = [''] * len(self._header_cache)
        
        now = self._get_now_str()
        user_link = f"https://t.me/{username}" if username != "без username" else "—"

        new_row[0] = user_link # ссылка на ник
        new_row[1] = str(telegram_id) # telegram_Id
        new_row[2] = str(full_name) # полное имя юзера
        new_row[3] = now # дата первого сообщения
        new_row[4] = now # дата последнего сообщения
        new_row[5] = '' # дата последнего нажатия на кнопку
        new_row[6] = str(nm_id) # артикул
        new_row[20] = str(full_name) # полное имя юзера

        await sheet.append_row(new_row)  

        # После добавления — найти строку юзера в гугл-таблице и сохранить в Redis в кэш 
        cell = await sheet.find(str(telegram_id))
        await self.redis.set(f"{self.REDIS_KEY_USER_ROW_POSITION_STRING}:{telegram_id}", cell.row)
    
    # === Быстрое обновление статусов ===
    async def update_buyer_last_time_message(
        self, 
        telegram_id: int,
        is_tap_to_keyboard: bool
    ) -> None:
        sheet = self.sheet or await self.get_sheet()
        row_index = await self.get_user_row(telegram_id)
        column_header_name = self.last_tap_column_name if is_tap_to_keyboard else self.last_message_column_name
        col_index = self._header_cache.get(column_header_name) 
        await sheet.update_cell(row_index, col_index, self._get_now_str())

    async def update_buyer_button_and_time(
        self,
        telegram_id: int,
        button_name: str,
        value: str,
        is_tap_to_keyboard: bool
    ) -> None:
        sheet = self.sheet or await self.get_sheet()
        row_index = await self.get_user_row(telegram_id)
        # Маппинг логических имён на реальные заголовки
        button_to_column = {
            "agree": self.header_row[7], # Условия , дальше по порядку
            "subscribe": self.header_row[8], # подписка на канал
            "order": self.header_row[9], # заказ сделан
            "photo_order": self.header_row[10], # скрин заказа GPT
            "receive": self.header_row[11], # заказ получен
            "feedback": self.header_row[12], # отзыв оставлен
            "photo_feedback": self.header_row[13], # скрин отзыва GPT
            "shk": self.header_row[14], # ШК разрезаны  
            "photo_shk": self.header_row[15], # фото разрезанных ШК GPT
            "requisites": self.header_row[16], # номер карты
            "phone_number": self.header_row[17], # номер телефона
            "bank": self.header_row[17], # банк 
            "amount": self.header_row[18] # сумма
        }
        button_col_name = button_to_column.get(button_name)
        time_col_name = (
            self.last_tap_column_name if is_tap_to_keyboard
            else self.last_message_column_name
        )
        # 2️⃣ Готовим список обновлений
        updates = []
        for column_name, val in [
            (button_col_name, value),
            (time_col_name, self._get_now_str())
        ]:
            col_index = self._header_cache[column_name]
            col_letter = chr(64 + col_index)
            cell_range = f"{col_letter}{row_index}"
            updates.append({"range": cell_range, "values": [[val]]})

        # 3️⃣ Один batch-запрос
        await sheet.batch_update(updates)


    async def write_requisites_into_google_sheets_and_update_last_time_message(
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
            self.header_row[16]: card_number or '-', # номер карты
            self.header_row[17]: phone_number or '-', # столбец Номер телефона
            self.header_row[18]: bank or '-', # столбец Банк
            self.header_row[19]: amount or '-', # столбец Сумма
            self.header_row[4]: self._get_now_str() # столбец Последнее сообщение
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
    
    async def load_nm_ids_ordered_list_into_redis(
        self,
        sheet_name: str,
        REDIS_KEY_NM_IDS_ORDERED_LIST: str,
    ) -> None:
        """
        Загружает пары артикул-количество из Google Sheets в Redis с префиксом nm_id_in_articles_sheet
        """
        sheet = await (await self.get_spreadsheet()).worksheet(sheet_name)
        values = await sheet.get_all_values()

        # Пропускаем заголовок
        pipe = self.redis.pipeline(transaction=True)
        for row in values[1:]:
            article = row[0].strip() # nm_id
            pipe.rpush(REDIS_KEY_NM_IDS_ORDERED_LIST, article) 
        await pipe.execute()
        logging.info(f"✅ Put {len(values)-1} nm_ids into {REDIS_KEY_NM_IDS_ORDERED_LIST}")
    
    async def get_instruction_template(self, sheet_instruction: str) -> str:
        """
        Возвращает шаблон инструкции из Google Sheets (ячейка A1).
        """
        sheet = await (await self.get_spreadsheet()).worksheet(sheet_instruction)
        instruction_cell = await sheet.acell("A1")
        return instruction_cell.value
    
    async def get_instruction(
        self,
        sheet_instruction: str,
        nm_id: str, 
        count: int,
        product_title: str
    ) -> str:
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
        
        # ссылка на товар на вб
        safe_url = f"https://www\\.wildberries\\.ru/catalog/{nm_id}/detail\\.aspx\\?targetUrl=SP"
        
        instruction_str = (
            instruction_str.replace("{", "{{").replace("}", "}}")
            .replace("{{nm_id}}", "{nm_id}")
            .replace("{{today_date}}", "{today_date}")
            .replace("{{count}}", "{count}")
            .replace("{{product_title}}", "{product_title}")
        )

        filled = instruction_str.format(
            nm_id=nm_id, 
            count=count,
            today_date=today_date,
            product_title=product_title
        )
        # 3️⃣ Экранируем MarkdownV2 спецсимволы в остальном тексте
        # но НЕ внутри конструкции [текст](ссылка)
        def escape_md_except_links(text: str) -> str:
            pattern = r"([_\[\]()~#+\-=|{}.!])"
            parts = re.split(r"(\[.*?\]\(.*?\))", text)  # разбиваем по ссылкам
            escaped_parts = []
            for part in parts:
                if part.startswith("[") and "](" in part:
                    escaped_parts.append(part)  # не трогаем ссылки
                else:
                    escaped_parts.append(re.sub(pattern, r"\\\1", part))
            return "".join(escaped_parts)

        safe_text = escape_md_except_links(filled)
        
        # 4️⃣ Подставляем безопасную ссылку
        safe_text = safe_text.replace(
            f"[{nm_id}](https://www.wildberries.ru/catalog/{nm_id}/detail.aspx?targetUrl=SP)",
            f"[{nm_id}]({safe_url})"
        )
        return safe_text