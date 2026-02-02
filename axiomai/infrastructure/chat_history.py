import json
from datetime import UTC, datetime

from dishka import AsyncContainer
from redis.asyncio import Redis

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager

MAX_CHAT_HISTORY = 10
PREDIALOG_TTL_SECONDS = 3600  # 1 hour


async def add_to_chat_history(
    di_container: AsyncContainer, buyer_id: int, user_message: str, assistant_response: str
) -> list[dict]:
    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        transaction_manager = await r_container.get(TransactionManager)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        if not buyer:
            return []

        chat_history = list(buyer.chat_history) if buyer.chat_history else []
        chat_history.append(
            {
                "user": user_message,
                "assistant": assistant_response,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        buyer.chat_history = chat_history[-MAX_CHAT_HISTORY:]
        await transaction_manager.commit()
        return buyer.chat_history


async def get_chat_history(di_container: AsyncContainer, buyer_id: int) -> list[dict]:
    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        return list(buyer.chat_history) if buyer and buyer.chat_history else []


def _predialog_redis_key(business_connection_id: str, chat_id: int) -> str:
    return f"predialog_history:{business_connection_id}:{chat_id}"


async def get_predialog_chat_history(
    redis: Redis, business_connection_id: str, chat_id: int
) -> list[dict[str, str]]:
    key = _predialog_redis_key(business_connection_id, chat_id)
    data = await redis.get(key)
    if not data:
        return []
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return json.loads(data)


async def add_predialog_chat_history(
    redis: Redis,
    business_connection_id: str,
    chat_id: int,
    user_message: str,
    assistant_response: str,
) -> list[dict[str, str]]:
    key = _predialog_redis_key(business_connection_id, chat_id)
    history = await get_predialog_chat_history(redis, business_connection_id, chat_id)
    history.append({
        "user": user_message,
        "assistant": assistant_response,
        "created_at": datetime.now(UTC).isoformat(),
    })
    history = history[-MAX_CHAT_HISTORY:]
    await redis.setex(key, PREDIALOG_TTL_SECONDS, json.dumps(history))
    return history


async def clear_predialog_chat_history(
    redis: Redis, business_connection_id: str, chat_id: int
) -> None:
    key = _predialog_redis_key(business_connection_id, chat_id)
    await redis.delete(key)
