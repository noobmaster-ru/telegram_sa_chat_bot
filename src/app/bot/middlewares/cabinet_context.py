import logging
import json
import time
import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional

from redis.asyncio import Redis

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery  # <-- ВАЖНО: здесь
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.infrastructure.apis.open_ai_requests_class import OpenAiRequestClass
from src.infrastructure.db.models import CabinetORM, CashbackTableORM, CashbackTableStatus
from src.tools.string_converter_class import StringConverter
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
        block_if_no_leads: bool,
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
        self.block_if_no_leads = block_if_no_leads  
        
        # watcher настроек (D2:H2 -> Redis)
        self._watchers_started: set[str] = set()
        
        # watcher остатка лидов -> в таблицу
        self._leads_watchers_started: set[str] = set()

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
            # Ищем кабинет по business_connection_id (с подгруженными relations)
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
        
        # ЛОГ ДЛЯ ОТЛАДКИ
        logger.info(
            "CabinetContext: cabinet_id=%s, leads_balance_attr=%r",
            cabinet.id,
            getattr(cabinet, "leads_balance", None),
        )
        # === 3a. Блокировка, если закончились лиды ===
        if self.block_if_no_leads:
            leads_balance = getattr(cabinet, "leads_balance", 0) or 0
            logger.info(
                "CabinetContext: after normalizing leads_balance=%s",
                leads_balance,
            )
            if leads_balance <= 0:
                # text = (
                #     "К сожалению, приём заявок на кэшбек временно приостановлен.\n"
                #     # "У продавца закончился лимит лидов.\n"
                #     "Попробуйте написать позже.\n"
                #     "Спасибо."
                # )
                
                # if isinstance(event, Message):
                #     await event.answer(text)
                # elif isinstance(event, CallbackQuery) and event.message:
                #     await event.message.answer(text)
                #     await event.answer()

                return  # не зовём handler → бот для клиентов молчит
        
        # # === 3б. Списываем лид при первом обращении клиента ===
        # if self.block_if_no_leads and isinstance(event, Message):
        #     await self._maybe_consume_lead(
        #         message=event,
        #         cabinet=cabinet,
        #         session_factory=session_factory,
        #         business_connection_id=business_connection_id,
        #     )
            
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
                redis_client=self.redis_client,
                REDIS_KEY_USER_ROW_POSITION_STRING=f"{self.REDIS_KEY_USER_ROW_POSITION_STRING}:{business_connection_id}"
            )
            # watcher настроек (D2:H2 -> Redis)
            if session_factory is not None and business_connection_id not in self._watchers_started:
                self._watchers_started.add(business_connection_id)
                asyncio.create_task(
                    self._watch_spreadsheet_loop(
                        business_connection_id=business_connection_id,
                        cabinet_id=cabinet.id,
                        spreadsheet=spreadsheet,
                        db_session_factory=session_factory,
                    )
                )
            # watcher остатка лидов -> в ячейку LEADS_REMAIN_CELL
            if session_factory is not None and business_connection_id not in self._leads_watchers_started:
                self._leads_watchers_started.add(business_connection_id)
                asyncio.create_task(
                    self._sync_leads_balance_loop(
                        business_connection_id=business_connection_id,
                        cabinet_id=cabinet.id,
                        spreadsheet=spreadsheet,
                        db_session_factory=session_factory,
                    )
                )
            self._sheets_cache[business_connection_id] = spreadsheet

        data["spreadsheet"] = spreadsheet
        
        # 6. Берём/создаём OpenAiRequestClass c СВОИМ instruction_template
        client_gpt_5 = self._gpt_cache.get(business_connection_id)
        if client_gpt_5 is None:
            # Тянем инструкцию ИМЕННО из таблицы этого кабинета
            instruction_template = await spreadsheet.get_instruction_template(
                constants.SETTINGS_SHEET_NAME_STR
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

    ### NEW: функция списания лида
    async def _maybe_consume_lead(
        self,
        message: Message,
        cabinet: CabinetORM,
        session_factory: async_sessionmaker[AsyncSession],
        business_connection_id: str,
    ) -> None:
        """Списываем 1 лид при первом сообщении конкретного клиента в этот кабинет."""
        if message.from_user is None:
            return

        client_id = message.from_user.id
        bot_id = message.bot.id 
        redis_key = f"fsm:{bot_id}:{business_connection_id}:{constants.REDIS_KEY_LEADS_USED}:{cabinet.id}"

        # SADD вернёт 1, если client_id добавился впервые → это новый лид
        try:
            added = await self.redis_client.sadd(redis_key, client_id)
        except Exception as e:
            logger.exception("Ошибка при работе с Redis в _maybe_consume_lead: %s", e)
            return

        if added != 1:
            # этого клиента уже считали как лид для этого кабинета - выходим
            return

        # Списываем лид в БД
        async with session_factory() as session:
            db_cabinet = await session.get(CabinetORM, cabinet.id)
            if db_cabinet is None:
                return

            current_balance = (db_cabinet.leads_balance or 0)
            if current_balance <= 0:
                # на момент списания уже 0 — просто не уходим в минус
                db_cabinet.leads_balance = 0
            else:
                db_cabinet.leads_balance = current_balance - 1

            await session.commit()
            await session.refresh(db_cabinet)

        # Обновляем объект в кэше/памяти
        cabinet.leads_balance = db_cabinet.leads_balance
        self._cabinet_cache[business_connection_id] = (time.time(), cabinet)
        logger.info(
            " Lead consumed for cabinet %s, client %s, new balance=%s",
            cabinet.id,
            client_id,
            cabinet.leads_balance,
        )
    
    async def _watch_spreadsheet_loop(
        self,
        business_connection_id: str,
        cabinet_id: int,
        spreadsheet: GoogleSheetClass,
        db_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """
        Фоновая задача: раз в N секунд читает настройки артикула из Google Sheets
        и складывает их в Redis/БД.
        """
        logger.info(
            "Start watcher for business_connection_id=%s, cabinet_id=%s",
            business_connection_id,
            cabinet_id,
        )
        while True:
            try:
                settings = await spreadsheet.get_data_from_settings_sheet() 
                # settings = {
                #     "nm_id": nm_id,
                #     "image_url": image_url,
                #     "nm_id_name": nm_id_name,
                #     "brand_name": brand_name,
                #     "instruction": instruction
                # }

                # ---- сохраняем в Redis, чтобы clients_bot быстро это читал ----
                redis_key = f"CABINET_SETTINGS:{business_connection_id}:product_settings"
                await self.redis_client.set(
                    redis_key,
                    json.dumps(settings, ensure_ascii=False),
                )

                # ---- (опционально) можем что-то обновлять в БД ----
                # async with db_session_factory() as session:
                #     ...
                #     await session.commit()

            except Exception:
                logger.exception(
                    "Ошибка в watcher-е Google Sheets для cabinet_id=%s",
                    cabinet_id,
                )
            await asyncio.sleep(constants.TIME_DELTA_CHECK_GOOGLE_SHEETS_SELLER_DATA_UPDATE)
            
    async def _sync_leads_balance_loop(
        self,
        business_connection_id: str,
        cabinet_id: int,
        spreadsheet: GoogleSheetClass,
        db_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """
        Фоновая задача: периодически читает leads_balance из БД
        и пишет его в таблицу (ячейка constants.LEADS_REMAIN_CELL).
        Например, раз в час.
        """
        logger.info(
            "Start leads watcher for business_connection_id=%s, cabinet_id=%s",
            business_connection_id,
            cabinet_id,
        )


        while True:
            try:
                # 1. Берём актуальный leads_balance из БД
                async with db_session_factory() as session:
                    db_cabinet = await session.get(CabinetORM, cabinet_id)
                    if db_cabinet is None:
                        logger.warning(
                            "Cabinet %s not found in DB in leads watcher, stop loop",
                            cabinet_id,
                        )
                        return

                    leads_balance = db_cabinet.leads_balance or 0

                # sheet = spreadsheet.settings_sheet or await spreadsheet.get_settings_sheet()
                # sheet = await (await spreadsheet.get_spreadsheet()).worksheet(constants.SETTINGS_SHEET_NAME_STR)
                sheet = await spreadsheet.get_settings_sheet()
                now = StringConverter.get_now_str()
                value_text = f"Остаток лидов: {leads_balance}, время обновления: {now}"
                # gspread-asyncio: обновление одной ячейки
                await sheet.batch_update([
                    {
                        "range": constants.LEADS_REMAIN_CELL,
                        "values": [[value_text]],
                    },
                    {
                        "range": constants.LEADS_REMAIN_CELL_UPPER,
                        "values": [[f"Остаток лидов, обновление раз в ~{constants.TIME_DELTA_CHECK_LEADS_REMAIN // 3600} часов"]],
                    },
                    # сюда можно добавить ещё диапазоны
                ])
                logger.info(
                    "Leads watcher: cabinet_id=%s, leads_balance=%s записан в %s",
                    cabinet_id,
                    leads_balance,
                    constants.LEADS_REMAIN_CELL,
                )

            except Exception:
                logger.exception(
                    "Ошибка в leads watcher-е для cabinet_id=%s",
                    cabinet_id,
                )

            await asyncio.sleep(constants.TIME_DELTA_CHECK_LEADS_REMAIN)