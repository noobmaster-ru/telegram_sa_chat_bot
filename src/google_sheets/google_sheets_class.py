import re
from datetime import datetime
from zoneinfo import ZoneInfo
from gspread import service_account
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials
from gspread_asyncio import AsyncioGspreadClientManager, AsyncioGspreadSpreadsheet, AsyncioGspreadWorksheet
import gspread_asyncio
import gspread
from typing import Any, Dict, List
from typing import Optional
import asyncio

class GoogleSheetClass:
    """Асинхронное взаимодействие с Google Sheets"""
    
    def __init__(self, service_account_json: str, table_url: str, buyers_sheet_name: str):
        self.service_account_json = service_account_json
        self.table_url = table_url
        self.BUYERS_SHEET_NAME = buyers_sheet_name
        
        # создаём асинхронного менеджера клиента
        def get_creds():
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            return Credentials.from_service_account_file(service_account_json, scopes=scopes)
        self._agcm = AsyncioGspreadClientManager(get_creds)
        self._client = None                        # gspread client (лениво создаётся)
        self._spreadsheet_cache = None             # кэш Spreadsheet
        self._header_cache: dict[str, list[str]] = {}  # кэш хедеров по листам
    
    async def _get_client(self):
        """Авторизация клиента (лениво, 1 раз за всё время работы)."""
        if self._client is None:
            self._client = await self._agcm.authorize()
        return self._client

    async def _get_spreadsheet(self) -> AsyncioGspreadSpreadsheet:
        """Возвращает spreadsheet по URL с кэшем."""
        if not self._spreadsheet_cache:
            client = await self._get_client()
            self._spreadsheet_cache = await client.open_by_url(self.table_url)
        return self._spreadsheet_cache
    
    @staticmethod
    def _get_now_str() -> str:
        """Текущее время в Москве в строковом формате"""
        return datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")
    
    async def get_nm_id(self, sheet_articles: str) -> str:
        spreadsheet = await self._get_spreadsheet()
        sheet = await spreadsheet.worksheet(sheet_articles)
        nm_id_cell = await sheet.acell("A2")
        return nm_id_cell.value
    
    async def delete_row(self, telegram_id: int) -> None:
        spreadsheet = await self._get_spreadsheet()
        sheet = await spreadsheet.worksheet(self.BUYERS_SHEET_NAME)
        all_rows = await sheet.get_all_values()

        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > 1 and row[1] == str(telegram_id):
                # delete row with telegram_id = telegram_id
                await sheet.delete_rows(i)
                print(f"[INFO] Deleted row for {telegram_id} user")
                return
        print(f"[WARN] User {telegram_id} not found in sheet!")
    
    async def get_instruction(self, sheet_instruction: str, nm_id: str) -> str:
        spreadsheet = await self._get_spreadsheet()
        sheet = await spreadsheet.worksheet(sheet_instruction)
        instruction_cell = await sheet.acell("A1")
        instruction_str = instruction_cell.value

        months = {
            1: "января",
            2: "февраля",
            3: "марта",
            4: "апреля",
            5: "мая",
            6: "июня",
            7: "июля",
            8: "августа",
            9: "сентября",
            10: "октября",
            11: "ноября",
            12: "декабря",
        }

        today = datetime.now(ZoneInfo("Europe/Moscow"))
        today_date = f"{today.day}_{months[today.month]}"

        # Экранируем фигурные скобки, кроме наших шаблонов
        instruction_str = (
            instruction_str.replace("{", "{{").replace("}", "}}")
            .replace("{{nm_id}}", "{nm_id}")
            .replace("{{today_date}}", "{today_date}")
        )

        filled = instruction_str.format(nm_id=nm_id, today_date=today_date)
        return re.sub(r"([_\[\]()~#+\-=|{}.!])", r"\\\1", filled)
    

    async def add_new_buyer(
        self,
        sheet_name: str,
        username: str,
        telegram_id: int,
        nm_id: str,
        status_agree: str = "None",
        status_subscribe_to_channel: str = "None",
        status_order: str = "None",
        status_order_received: str = "None",
        status_feedback: str = "None",
        status_shk: str = "None",
        requisites: str = "None",
        phone_number: str = "None",
        bank: str = "None",
        amount: str = "None",
        paid: str = "None",
    ) -> None:
        spreadsheet = await self._get_spreadsheet()
        sheet = await spreadsheet.worksheet(sheet_name)
        now = self._get_now_str()
        user_link = f"https://t.me/{username}" if username != "без username" else "—"

        new_row = [
            user_link,
            str(telegram_id),
            now,
            now,
            nm_id,
            status_agree,
            status_subscribe_to_channel,
            status_order,
            status_order_received,
            status_feedback,
            status_shk,
            requisites,
            phone_number,
            bank,
            amount,
            paid,
        ]
        await sheet.append_row(new_row, value_input_option="USER_ENTERED")
        print(f"[INFO] Added new buyer {telegram_id}")

    async def update_buyer_last_time_message(self, telegram_id: int) -> None:
        spreadsheet = await self._get_spreadsheet()
        sheet = await spreadsheet.worksheet(self.BUYERS_SHEET_NAME)
        all_rows = await sheet.get_all_values()
        now = self._get_now_str()

        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > 1 and row[1] == str(telegram_id):
                await sheet.update_cell(i, 4, now)
                print(f"[INFO] Updated last message for {telegram_id} → {now}")
                return

        print(f"[WARN] User {telegram_id} not found in sheet!")


    async def _get_sheet(self, sheet_name: Optional[str] = None):
        """Возвращает конкретный лист по имени (или buyers_sheet_name по умолчанию)."""
        spreadsheet = await self._get_spreadsheet()
        return await spreadsheet.worksheet(sheet_name or self.BUYERS_SHEET_NAME)


    async def _get_header(self, sheet) -> list[str]:
        """Кэшируем первую строку (заголовки)."""
        if sheet.title not in self._header_cache:
            header = await sheet.row_values(1)
            self._header_cache[sheet.title] = header
        return self._header_cache[sheet.title]
    
    async def update_buyer_button_status(
        self,
        sheet_name: str,
        telegram_id: int,
        button_name: str,
        value: str,
    ) -> None:
        """⚡ Быстрая версия обновления одной ячейки."""
        sheet = await self._get_sheet(sheet_name)
        header = await self._get_header(sheet)

        # Соответствие кнопок и столбцов
        col_map = [
            "agree", "subscribe", "order", "receive",
            "feedback", "shk", "requisites",
            "phone_number", "bank", "amount"
        ]
        # Привязка к хедерам (сдвиг на +5, как у тебя)
        new_col_map = {
            k: header[i + 5] for i, k in enumerate(col_map) if i + 5 < len(header)
        }

        col_name = new_col_map.get(button_name)
        if not col_name:
            print(f"[WARN] Unknown button_name: {button_name}")
            return

        try:
            cell = await sheet.find(str(telegram_id))
        except Exception:
            print(f"[WARN] User {telegram_id} not found for update!")
            return

        # Находим индекс столбца по имени
        if col_name not in header:
            print(f"[WARN] Column '{col_name}' not found.")
            return

        col_index = header.index(col_name) + 1
        cell_label = rowcol_to_a1(cell.row, col_index)

        await sheet.batch_update([{
            "range": cell_label,
            "values": [[value]]
        }])

        await self.update_buyer_last_time_message(telegram_id)
        print(f"[INFO] Updated {button_name} for {telegram_id} → {value}")   

    # async def update_buyer_button_status(
    #     self,
    #     sheet_name: str,
    #     telegram_id: int,
    #     button_name: str,
    #     value: str,
    # ) -> None:
    #     spreadsheet = await self._get_spreadsheet()
    #     sheet = await spreadsheet.worksheet(sheet_name)
    #     records = await sheet.get_all_records()
    #     if not records:
    #         print("[WARN] No records found in sheet.")
    #         return

    #     keys = list(records[0].keys())
    #     col_map = [
    #         "agree",
    #         "subscribe",
    #         "order",
    #         "receive",
    #         "feedback",
    #         "shk",
    #         "requisites",
    #         "phone_number",
    #         "bank",
    #         "amount"
    #     ]

    #     new_col_map = {k: keys[i + 5] for i, k in enumerate(col_map) if i + 5 < len(keys)}

    #     header_row = await sheet.row_values(1)
    #     for i, record in enumerate(records, start=2):
    #         if str(record.get(keys[1])) == str(telegram_id):
    #             col_name = new_col_map.get(button_name)
    #             if not col_name:
    #                 print(f"[WARN] Unknown button_name: {button_name}")
    #                 return
    #             if col_name not in header_row:
    #                 print(f"[WARN] Column '{col_name}' not found.")
    #                 return
    #             col_index = header_row.index(col_name) + 1
    #             await sheet.update_cell(i, col_index, value)
    #             await self.update_buyer_last_time_message(telegram_id)
    #             print(f"[INFO] Updated {button_name} for {telegram_id} → {value}")
    #             return

    #     print(f"[WARN] User {telegram_id} not found for update!")