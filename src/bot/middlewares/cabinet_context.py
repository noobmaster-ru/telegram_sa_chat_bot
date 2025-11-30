from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.apis.google_sheets_class import GoogleSheetClass
from src.db.models import CabinetORM, CashbackTableORM, CashbackTableStatus


class CabinetContextMiddleware(BaseMiddleware):
    def __init__(
        self,
        redis_client,
        service_account_json: str,
        buyers_sheet_name: str,
        REDIS_KEY_USER_ROW_POSITION_STRING: str,
    ) -> None:
        self.redis_client = redis_client
        self.service_account_json = service_account_json
        self.buyers_sheet_name = buyers_sheet_name
        self.REDIS_KEY_USER_ROW_POSITION_STRING = REDIS_KEY_USER_ROW_POSITION_STRING

        # кэш: business_connection_id -> GoogleSheetClass
        self._sheets_cache: dict[str, GoogleSheetClass] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # 1. Достаём business_connection_id
        business_connection_id: Optional[str] = None

        if isinstance(event, Message):
            business_connection_id = getattr(event, "business_connection_id", None)
        elif isinstance(event, CallbackQuery) and isinstance(event.message, Message):
            business_connection_id = getattr(event.message, "business_connection_id", None)

        if not business_connection_id:
            # не бизнес-апдейт, просто пробрасываем
            return await handler(event, data)

        # 2. Достаём session_factory из workflow_data
        session_factory: Optional[async_sessionmaker[AsyncSession]] = data.get(
            "db_session_factory"
        )
        if session_factory is None:
            data["cabinet"] = None
            data["spreadsheet"] = None
            return await handler(event, data)

        # 3. Ищем кабинет по business_connection_id и
        # сразу подгружаем cashback_tables и articles (eager load)
        async with session_factory() as session:
            stmt = (
                select(CabinetORM)
                .options(
                    selectinload(CabinetORM.cashback_tables),
                    selectinload(CabinetORM.articles),
                )
                .where(CabinetORM.business_connection_id == business_connection_id)
            )
            result = await session.execute(stmt)
            cabinet: Optional[CabinetORM] = result.scalar_one_or_none()

        if cabinet is None:
            data["cabinet"] = None
            data["spreadsheet"] = None
            return await handler(event, data)

        data["cabinet"] = cabinet

        # 4. Выбираем таблицу кэшбека из уже загруженного списка
        cashback_table = None
        for t in cabinet.cashback_tables:
            if t.status not in (CashbackTableStatus.DISABLED, CashbackTableStatus.EXPIRED):
                cashback_table = t
                break

        if cashback_table is None and cabinet.cashback_tables:
            cashback_table = cabinet.cashback_tables[0]

        if cashback_table is None:
            data["spreadsheet"] = None
            return await handler(event, data)

        # 5. Берём/создаём GoogleSheetClass для этой таблицы
        spreadsheet = self._sheets_cache.get(business_connection_id)
        if spreadsheet is None:
            spreadsheet = GoogleSheetClass(
                service_account_json=self.service_account_json,
                spreadsheet_id=cashback_table.table_id,
                buyers_sheet_name=self.buyers_sheet_name,
                redis_client=self.redis_client,
                REDIS_KEY_USER_ROW_POSITION_STRING=self.REDIS_KEY_USER_ROW_POSITION_STRING,
            )
            self._sheets_cache[business_connection_id] = spreadsheet

        data["spreadsheet"] = spreadsheet

        return await handler(event, data)