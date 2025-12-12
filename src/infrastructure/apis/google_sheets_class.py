import json
import logging
from datetime import datetime
from typing import List, Dict
from redis.asyncio import Redis
from gspread_asyncio import AsyncioGspreadClientManager, AsyncioGspreadSpreadsheet
from google.oauth2.service_account import Credentials

from src.tools.string_converter_class import StringConverter
from src.core.config import constants

class GoogleSheetClass:
    """⚡ Быстрое асинхронное взаимодействие с Google Sheets с кэшами и пакетными апдейтами."""
    def __init__(
        self, 
        service_account_json: str,
        spreadsheet_id: str, 
        redis_client: Redis,
        REDIS_KEY_USER_ROW_POSITION_STRING: str
    ):
        # Авторизация и получение объекта листа
        self.spreadsheet_id = spreadsheet_id
        self.buyers_sheet_name = constants.BUYERS_SHEET_NAME_STR
        self.settings_sheet_name = constants.SETTINGS_SHEET_NAME_STR
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
        self.buyers_sheet = None
        self.settings_sheet = None

        # первая строка - названия столбцов
        self.header_row = None 
        self._header_cache = None
        
        # названия столбцов: "Последнее сообщение", "Последнее нажатие на кнопку"
        self.last_message_column_name = None
        self.last_tap_column_name = None
        
        # redis
        self.redis = redis_client
        self.REDIS_KEY_USER_ROW_POSITION_STRING = REDIS_KEY_USER_ROW_POSITION_STRING

    
    async def get_client(self):
        if self.client is None:
            self.client = await self.agcm.authorize()
        return self.client

    async def get_spreadsheet(self) -> AsyncioGspreadSpreadsheet:
        if self.spreadsheet is None:
            client = await self.get_client()
            self.spreadsheet = await client.open_by_key(self.spreadsheet_id)
        return self.spreadsheet
    
    async def get_buyers_sheet(self):
        if self.buyers_sheet is None :
            self.buyers_sheet = await self.spreadsheet.worksheet(self.buyers_sheet_name)
            self.header_row = await self.buyers_sheet.row_values(1)
            # запишем в класс названия столбцов некоторых, чтобы облечить прод
            self.last_message_column_name = self.header_row[4]
            self.last_tap_column_name = self.header_row[6]
            self._header_cache = {header: idx + 1 for idx, header in enumerate(self.header_row)}
        return self.buyers_sheet 
    
    async def get_settings_sheet(self):
        if self.settings_sheet is None:
            self.settings_sheet = await (await self.get_spreadsheet()).worksheet(self.settings_sheet_name)
            # self.settings_sheet = await self.spreadsheet.worksheet(self.settings_sheet_name)
        return self.settings_sheet 

    async def get_user_row(self, telegram_id: int) -> int:
        """Возвращает индекс строки из Redis или ищет в таблице, если в кэше нет."""
        key = f"{self.REDIS_KEY_USER_ROW_POSITION_STRING}:{telegram_id}"
        row_index = await self.redis.get(key)
        if row_index:
            return int(row_index)

        # ❌ Если нет в Redis — ищем в таблице
        sheet = self.buyers_sheet or await self.get_buyers_sheet()
        cell = await sheet.find(str(telegram_id))
        row_index = cell.row

        # ✅ Сохраняем в Redis
        await self.redis.set(key, row_index)
        return row_index 
  
    # === Основные операции ===
    async def add_new_buyer(
        self, 
        username: str, 
        full_name: str, 
        telegram_id: int, 
        nm_id: int,
        msg_text: str,
    ) -> None:
        """Возвращает индекс строки из Redis или ищет в таблице, если в кэше нет."""
        key = f"{self.REDIS_KEY_USER_ROW_POSITION_STRING}:{telegram_id}"
        row_index = await self.redis.get(key)
        if row_index:
            return # if user already in google sheets - dont add him, skip
        
        sheet = self.buyers_sheet or await self.get_buyers_sheet()
        new_row = [''] * len(self._header_cache)
        
        now = StringConverter.get_now_str()
        user_link = f"https://t.me/{username}" if username != "без username" else "—"

        new_row[0] = user_link # ссылка на ник
        new_row[1] = str(telegram_id) # telegram_Id
        new_row[2] = str(full_name) # полное имя юзера
        new_row[3] = now # дата первого сообщения
        new_row[4] = now # дата последнего сообщения
        new_row[5] = msg_text # текст последнего сообщения
        new_row[6] = '' # дата последнего нажатия на кнопку
        new_row[7] = str(nm_id) # артикул
        new_row[19] = str(full_name) # полное имя юзера

        await sheet.append_row(new_row)  

        # После добавления — найти строку юзера в гугл-таблице и сохранить в Redis в кэш 
        cell = await sheet.find(str(telegram_id))
        await self.redis.set(f"{self.REDIS_KEY_USER_ROW_POSITION_STRING}:{telegram_id}", cell.row)
    
    # === Быстрое обновление статусов ===
    async def update_buyer_last_time_message(
        self, 
        telegram_id: int,
        text: str
    ) -> None:
        sheet = self.buyers_sheet or await self.get_buyers_sheet()
        row_index = await self.get_user_row(telegram_id)
        column_header_name =  self.last_message_column_name 
        col_index = self._header_cache.get(column_header_name) 
        
        
        # Маппинг из логических имен в заголовки
        fields = {
            self.header_row[4]: StringConverter.get_now_str(), # столбец Последнее нажатия на кнопку
            self.header_row[5]: text, # столбец Текст последнего собщения
        }
        # Подготавливаем все апдейты для batch_update
        updates = []
        for column_name, value in fields.items():
            col_index = self._header_cache[column_name]
            # Конвертация номера столбца в букву (например 14 → N)
            col_letter = chr(64 + col_index)
            cell_range = f"{col_letter}{row_index}"
            updates.append({"range": cell_range, "values": [[value]]})
        
        # Один батч-запрос к API
        await sheet.batch_update(updates)

    async def update_buyer_button_and_time(
        self,
        telegram_id: int,
        button_name: str,
        value: str,
        is_tap_to_keyboard: bool
    ) -> None:
        sheet = self.buyers_sheet or await self.get_buyers_sheet()
        row_index = await self.get_user_row(telegram_id)
        # Маппинг логических имён на реальные заголовки
        button_to_column = {
            "agree": self.header_row[8], # Условия , дальше по порядку
            "order": self.header_row[9], # заказ сделан
            "photo_order": self.header_row[10], # скрин заказа GPT
            "receive": self.header_row[11], # заказ получен
            "feedback": self.header_row[12], # отзыв оставлен
            "photo_feedback": self.header_row[13], # скрин отзыва GPT
            "shk": self.header_row[14], # ШК разрезаны  
            "photo_shk": self.header_row[15], # фото разрезанных ШК GPT
            "phone_number": self.header_row[16], # номер телефона
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
            (time_col_name, StringConverter.get_now_str())
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
        phone_number: str,
        bank: str,
        amount: str,
    ) -> None:
        """Обновляет реквизиты (карта, сумма, телефон, банк) одной операцией."""
        sheet = self.buyers_sheet or await self.get_buyers_sheet() 
        row_index = await self.get_user_row(telegram_id)
        
        phone_number_hash = StringConverter.convert_phone_to_hash_format(phone_number)
        # чтобы Google Sheets сохранил +7, добавляем апостроф
        # fixed_phone = f"'{phone_number_hash}" if phone_number_hash else "-"
        
        # Маппинг из логических имен в заголовки
        fields = {
            self.header_row[4]: StringConverter.get_now_str(), # столбец Последнее сообщение
            self.header_row[16]: phone_number_hash, # столбец Номер телефона
            self.header_row[17]: bank or '-', # столбец Банк
            self.header_row[18]: amount or '-', # столбец Сумма
        }

        # Подготавливаем все апдейты для batch_update
        updates = []
        for column_name, value in fields.items():
            col_index = self._header_cache[column_name]
            # Конвертация номера столбца в букву (например 14 → N)
            col_letter = chr(64 + col_index)
            cell_range = f"{col_letter}{row_index}"
            updates.append({"range": cell_range, "values": [[value]]})
        
        logging.info(f"  user: {telegram_id}, writes requisites into GoogleSheet: {phone_number}, {bank}, {amount}")
        # Один батч-запрос к API
        await sheet.batch_update(updates)#, value_input_option="RAW")
    

    async def get_instruction_template(self, sheet_instruction: str) -> str:
        """
        Возвращает шаблон инструкции из Google Sheets (ячейка A1).
        """
        # sheet = await (await self.get_spreadsheet()).worksheet(sheet_instruction)
        sheet = await self.get_settings_sheet()
        instruction_cell = await sheet.acell(constants.INSTRUCTION_CELL_TEMPLATE)
        return instruction_cell.value
    
    async def get_instruction(
        self,
        sheet_settings: str,
    ) -> str:
        # sheet = await (await self.get_spreadsheet()).worksheet(sheet_settings)
        sheet = await self.get_settings_sheet()
        instruction_cell = await sheet.acell(constants.INSTRUCTION_CELL)
        instruction_str = instruction_cell.value
        safe_text_instruction = StringConverter.escape_markdown_v2(instruction_str)
        return safe_text_instruction

    async def get_all_telegram_id(self) -> List[int]:
        sheet = self.buyers_sheet or await self.get_buyers_sheet()
        all_values = await sheet.get_all_values() 
        telegram_ids = []    
        # Проходим по всем строкам, начиная со второй (индекс 1 в Python), чтобы пропустить заголовок
        for row_values in all_values[1:]:
            # Проверяем, что строка не пустая и содержит нужный столбец
            if row_values:
                try:
                    # Пытаемся преобразовать значение в целое число
                    tg_id = int(row_values[1])
                    telegram_ids.append(tg_id)
                except ValueError:
                    # Игнорируем строки, где значение не является числом
                    continue            
        return telegram_ids


    async def get_data_from_settings_sheet(self) -> tuple[int, str, str, str, str]:
        """
        Читает Настройка!C2:H2 и возвращает:
        nm_id, image_url, article_title, brand_name, instruction
        """

        # sheet = self.settings_sheet or await self.get_settings_sheet()
        # sheet = await (await self.get_spreadsheet()).worksheet(self.settings_sheet_name)
        sheet = await self.get_settings_sheet()
        
        # [[D2, E2, F2, G2, H2]]
        values = await sheet.get("D2:H2")
        row = values[0] if values else ["", "", "", "", ""]

        nm_id_str, image_url, nm_id_name, brand_name, instruction = row
        nm_id = int(nm_id_str) if nm_id_str.strip().isdigit() else None

        settings = {
          "nm_id": nm_id,
          "image_url": image_url,
          "nm_id_name": nm_id_name,
          "brand_name": brand_name,
          "instruction": instruction
        }
        now = StringConverter.get_now_str()
        text = f"Время последнего чтения информации: {now}"

        # gspread-asyncio: обновление одной ячейки
        await sheet.batch_update([
            {
                "range": constants.TIME_UPDATE_CELL,
                "values": [[text]],
            },
            {
                "range": constants.TIME_UPDATE_CELL_UPPER,
                "values": [[f"Обновление информации в бд раз в ~{constants.TIME_DELTA_CHECK_GOOGLE_SHEETS_SELLER_DATA_UPDATE // 60} минут"]],
            },
            # сюда можно добавить ещё диапазоны
        ])
        return settings