import logging
from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Awaitable, Dict, Any

import redis.asyncio as asyncredis


class CheckRedisUserMiddleware(BaseMiddleware):
    def __init__(self, redis_client: asyncredis.Redis, redis_key: str):
        super().__init__()
        self.redis = redis_client
        self.redis_key = redis_key
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        telegram_id = event.from_user.id

        # Проверяем наличие ID в Redis
        if await self.redis.sismember(self.redis_key, str(telegram_id)):
            logging.info(f"user_id {telegram_id} in Redis, skip him")
            return  # Прерываем выполнение — хэндлеры не вызываются

        # новый пользователь - начинаем обработку
        return await handler(event, data)
