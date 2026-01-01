# src/app/bot/utils/leads.py

import time
import logging
from typing import Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.db.models import CabinetORM
from src.core.config import constants

logger = logging.getLogger(__name__)


async def consume_lead_for_cabinet(
    *,
    redis_client: Redis,
    session_factory: async_sessionmaker[AsyncSession],
    cabinet: CabinetORM,
    client_id: int,
    bot_id: int,
    business_connection_id: Optional[str],
    cabinet_cache: Optional[dict[str, tuple[float, CabinetORM]]] = None,
) -> None:
    """
    Списывает 1 лид для (cabinet, client_id), если ещё не списывали.

    Идемпотентность за счёт Redis-множества:
    - если клиент уже был, второй раз ничего не списываем.
    """
    if business_connection_id is None:
        return

    redis_key = f"fsm:{bot_id}:{business_connection_id}:{constants.REDIS_KEY_LEADS_USED}:{cabinet.id}"

    try:
        # SADD вернёт 1, если client_id добавился впервые → новый лид
        added = await redis_client.sadd(redis_key, client_id)
    except Exception as e:
        logger.exception("Ошибка при работе с Redis в consume_lead_for_cabinet: %s", e)
        return

    if added != 1:
        # этого клиента уже считали как лид для этого кабинета - выходим
        return

    # Списываем лид в БД
    async with session_factory() as session:
        db_cabinet = await session.get(CabinetORM, cabinet.id)
        if db_cabinet is None:
            return

        current_balance = db_cabinet.leads_balance or 0
        if current_balance <= 0:
            db_cabinet.leads_balance = 0
        else:
            db_cabinet.leads_balance = current_balance - 1

        await session.commit()
        await session.refresh(db_cabinet)

    # Обновляем объект в памяти (кабинет из middleware)
    cabinet.leads_balance = db_cabinet.leads_balance

    # Если ты хочешь одновременно обновлять кэш middleware,
    # можно передать сюда self._cabinet_cache из middleware и обновить его:
    if cabinet_cache is not None and business_connection_id is not None:
        cabinet_cache[business_connection_id] = (time.time(), cabinet)

    logger.info(
        "Lead consumed for cabinet %s, client %s, new balance=%s",
        cabinet.id,
        client_id,
        cabinet.leads_balance,
    )