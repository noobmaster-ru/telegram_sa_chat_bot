import logging
import json
import time
from typing import Any, Awaitable, Callable, Dict, Optional

from redis.asyncio import Redis

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass
from src.db.models import CabinetORM, CashbackTableORM, CashbackTableStatus
from src.core.config import constants
logger = logging.getLogger(__name__)


class CabinetContextMiddleware(BaseMiddleware):
    def __init__(
        self,
        redis_client,
        service_account_json: str,
        buyers_sheet_name: str,
        REDIS_KEY_USER_ROW_POSITION_STRING: str,

        # Параметры для OpenAI-клиента
        openai_api_key: str,
        gpt_model_name: str,
        gpt_model_name_photo: str,
        proxy: str | None,
        max_tokens: int,
        max_output_tokens_photo: int,
        temperature: float,
        reasoning: str,
    ) -> None:
        self.redis_client = redis_client
        self.service_account_json = service_account_json
        self.buyers_sheet_name = buyers_sheet_name
        self.REDIS_KEY_USER_ROW_POSITION_STRING = REDIS_KEY_USER_ROW_POSITION_STRING

        # OpenAI config
        self.openai_api_key = openai_api_key
        self.gpt_model_name = gpt_model_name
        self.gpt_model_name_photo = gpt_model_name_photo
        self.proxy = proxy
        self.max_tokens = max_tokens
        self.max_output_tokens_photo = max_output_tokens_photo
        self.temperature = temperature
        self.reasoning = reasoning
        
        # кэш: business_connection_id -> GoogleSheetClass
        self._sheets_cache: dict[str, GoogleSheetClass] = {}
        # кэш: business_connection_id -> OpenAiRequestClass
        self._gpt_cache: dict[str, OpenAiRequestClass] = {}
        # кэш cabinet'ов: business_connection_id -> (timestamp, CabinetORM)
        self._cabinet_cache: dict[str, tuple[float, CabinetORM]] = {}
        # TTL для кабинета, например 120 секунд
        self._cabinet_ttl_seconds = constants.CABINET_CONTEXT_TTL_SECONDS
        
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
            data["client_gpt_5"] = None
            return await handler(event, data)
        
        now = time.time()
        cached_entry = self._cabinet_cache.get(business_connection_id)
        cabinet: Optional[CabinetORM] = None

        if cached_entry is not None:
            ts, cached_cabinet = cached_entry
            if now - ts < self._cabinet_ttl_seconds:
                cabinet = cached_cabinet
        
        if cabinet is None:
            # 3. Ищем кабинет по business_connection_id (с подгруженными relations)
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
                data["client_gpt_5"] = None
                return await handler(event, data)
            
            # положили в кэш
            self._cabinet_cache[business_connection_id] = (now, cabinet)
        
        data["cabinet"] = cabinet

        # 4. Выбираем актуальную таблицу кэшбека
        cashback_table: Optional[CashbackTableORM] = None
        for t in cabinet.cashback_tables:
            if t.status not in (CashbackTableStatus.DISABLED, CashbackTableStatus.EXPIRED):
                cashback_table = t
                break

        if cashback_table is None and cabinet.cashback_tables:
            cashback_table = cabinet.cashback_tables[0]

        if cashback_table is None:
            data["spreadsheet"] = None
            data["client_gpt_5"] = None
            return await handler(event, data)

        # 5. Берём/создаём GoogleSheetClass для этой таблицы
        spreadsheet = self._sheets_cache.get(business_connection_id)
        if spreadsheet is None:
            spreadsheet = GoogleSheetClass(
                service_account_json=self.service_account_json,
                spreadsheet_id=cashback_table.table_id,
                buyers_sheet_name=self.buyers_sheet_name,
                redis_client=self.redis_client,
                REDIS_KEY_USER_ROW_POSITION_STRING=f"{self.REDIS_KEY_USER_ROW_POSITION_STRING}:{business_connection_id}"
            )
            self._sheets_cache[business_connection_id] = spreadsheet

        data["spreadsheet"] = spreadsheet
        
        # 6. Берём/создаём OpenAiRequestClass c СВОИМ instruction_template
        client_gpt_5 = self._gpt_cache.get(business_connection_id)
        if client_gpt_5 is None:
            # Тянем инструкцию ИМЕННО из таблицы этого кабинета
            instruction_template = await spreadsheet.get_instruction_template(
                constants.INSTRUCTION_SHEET_NAME_STR
            )

            client_gpt_5 = OpenAiRequestClass(
                OPENAI_API_KEY=self.openai_api_key,
                GPT_MODEL_NAME=self.gpt_model_name,
                GPT_MODEL_NAME_PHOTO_ANALYSIS=self.gpt_model_name_photo,
                PROXY=self.proxy,
                instruction_template=instruction_template,
                max_tokens=self.max_tokens,
                max_output_tokens_photo_analysis=self.max_output_tokens_photo,
                temperature=self.temperature,
                reasoning=self.reasoning,
            )
            self._gpt_cache[business_connection_id] = client_gpt_5

        data["client_gpt_5"] = client_gpt_5
        
        return await handler(event, data)