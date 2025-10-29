import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional
from google.oauth2.service_account import Credentials
from gspread_asyncio import AsyncioGspreadClientManager, AsyncioGspreadSpreadsheet
from gspread.utils import rowcol_to_a1
import json

class GoogleSheetClass:
    """⚡ Быстрое асинхронное взаимодействие с Google Sheets с кэшами и пакетными апдейтами."""
    def __init__(self, service_account_json: str, table_url: str, buyers_sheet_name: str):
        self.service_account_json = service_account_json
        self.table_url = table_url
        self.BUYERS_SHEET_NAME = buyers_sheet_name
        
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
        self._agcm = AsyncioGspreadClientManager(lambda: self._creds)
        self._client = None
        self._spreadsheet_cache: Optional[AsyncioGspreadSpreadsheet] = None

        # Кэши
        self._header_cache: dict[str, list[str]] = {}
        self._row_index_cache: dict[str, dict[str, int]] = {}

        # Очередь для фоновых обновлений
        self._update_queue: asyncio.Queue = asyncio.Queue()
        self._background_task = None
    
    # === Авторизация и кэширование ===
    async def _get_client(self):
        if self._client is None:
            self._client = await self._agcm.authorize()
        return self._client

    async def _get_spreadsheet(self) -> AsyncioGspreadSpreadsheet:
        if not self._spreadsheet_cache:
            client = await self._get_client()
            self._spreadsheet_cache = await client.open_by_url(self.table_url)
        return self._spreadsheet_cache

    async def _get_sheet(self, sheet_name: Optional[str] = None):
        spreadsheet = await self._get_spreadsheet()
        return await spreadsheet.worksheet(sheet_name or self.BUYERS_SHEET_NAME)

    
    # === Кэширование заголовков и индексов ===
    async def _get_header(self, sheet) -> list[str]:
        if sheet.title not in self._header_cache:
            header = await sheet.row_values(1)
            self._header_cache[sheet.title] = header
        return self._header_cache[sheet.title]

    async def _build_row_index_cache(self, sheet) -> dict[str, int]:
        all_rows = await sheet.get_all_values()
        mapping = {}
        for i, row in enumerate(all_rows[1:], start=2):
            if len(row) > 1 and row[1]:
                mapping[row[1]] = i
        self._row_index_cache[sheet.title] = mapping
        return mapping

    async def _get_row_index(self, sheet, telegram_id: int) -> Optional[int]:
        cache = self._row_index_cache.get(sheet.title)
        if not cache:
            cache = await self._build_row_index_cache(sheet)
        return cache.get(str(telegram_id))
    
    # === Утилиты ===
    @staticmethod
    def _get_now_str() -> str:
        return datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")
    
    # === Основные операции ===

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
        sheet = await self._get_sheet(sheet_name)
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

        # обновляем кэш строки
        if sheet.title in self._row_index_cache:
            self._row_index_cache[sheet.title][str(telegram_id)] = len(self._row_index_cache[sheet.title]) + 2

        print(f"[INFO] Added new buyer {telegram_id}")

    async def delete_row(self, telegram_id: int) -> None:
        sheet = await self._get_sheet()
        row_index = await self._get_row_index(sheet, telegram_id)
        if not row_index:
            print(f"[WARN] User {telegram_id} not found!")
            return
        await sheet.delete_rows(row_index)
        self._row_index_cache.get(sheet.title, {}).pop(str(telegram_id), None)
        print(f"[INFO] Deleted row for {telegram_id}")

    # === Быстрое обновление статусов ===
    async def update_buyer_last_time_message(self, telegram_id: int) -> None:
        """Быстрое обновление колонки 'последнее сообщение'."""
        sheet = await self._get_sheet()
        header = await self._get_header(sheet)
        row_index = await self._get_row_index(sheet, telegram_id)
        if not row_index:
            print(f"[WARN] User {telegram_id} not found!")
            return
        now = self._get_now_str()
        await sheet.batch_update([{
            "range": rowcol_to_a1(row_index, 4),
            "values": [[now]]
        }])
        print(f"[INFO] Updated last message for {telegram_id} → {now}")
    
    async def update_buyer_button_status(
        self,
        sheet_name: str,
        telegram_id: int,
        button_name: str,
        value: str,
    ) -> None:
        sheet = await self._get_sheet(sheet_name)
        header = await self._get_header(sheet)
        row_index = await self._get_row_index(sheet, telegram_id)
        if not row_index:
            print(f"[WARN] User {telegram_id} not found!")
            return

        col_map = [
            "agree", "subscribe", "order", "receive",
            "feedback", "shk", "requisites", "phone_number", "bank", "amount"
        ]
        new_col_map = {k: header[i + 5] for i, k in enumerate(col_map) if i + 5 < len(header)}
        col_name = new_col_map.get(button_name)
        if not col_name:
            print(f"[WARN] Unknown button_name: {button_name}")
            return

        if col_name not in header:
            print(f"[WARN] Column '{col_name}' not found.")
            return

        col_index = header.index(col_name) + 1
        now = self._get_now_str()

        # Добавляем обновление в очередь
        await self._update_queue.put((
            sheet,
            [
                {"range": rowcol_to_a1(row_index, col_index), "values": [[value]]},
                {"range": rowcol_to_a1(row_index, 4), "values": [[now]]},
            ],
        ))

        # Если фоновая задача ещё не запущена — запускаем
        if not self._background_task or self._background_task.done():
            self._background_task = asyncio.create_task(self._background_updater())

    async def _background_updater(self):
        """Периодически отправляет пакет обновлений в Google Sheets."""
        await asyncio.sleep(0.5)  # даём возможность накопиться изменениям
        updates_by_sheet: dict[Any, list[dict]] = {}

        while not self._update_queue.empty():
            sheet, updates = await self._update_queue.get()
            updates_by_sheet.setdefault(sheet, []).extend(updates)

        # Отправляем обновления пакетами
        for sheet, updates in updates_by_sheet.items():
            try:
                await sheet.batch_update(updates)
                print(f"[BATCH] Updated {len(updates)} cells on '{sheet.title}'")
            except Exception as e:
                print(f"[ERROR] Batch update failed on {sheet.title}: {e}")

    # === Прочие методы ===
    async def get_nm_id(self, sheet_articles: str) -> str:
        sheet = await (await self._get_spreadsheet()).worksheet(sheet_articles)
        nm_id_cell = await sheet.acell("A2")
        return nm_id_cell.value

    async def get_instruction(self, sheet_instruction: str, nm_id: str) -> str:
        sheet = await (await self._get_spreadsheet()).worksheet(sheet_instruction)
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