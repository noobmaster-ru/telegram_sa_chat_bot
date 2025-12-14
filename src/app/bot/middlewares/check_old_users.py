from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from redis.asyncio import Redis

from src.core.config import constants


class CheckUserInOldUsers(BaseMiddleware):
    def __init__(self, redis: Redis):
        super().__init__()
        self.redis = redis

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        """
        Middleware определяет, является ли пользователь старым клиентом.
        Результат кладёт в data["is_old_user"] (bool).
        """
        if isinstance(event, Message):
            business_connection_id = getattr(event, "business_connection_id", None)
        elif isinstance(event, CallbackQuery) and isinstance(event.message, Message):
            business_connection_id = getattr(event.message, "business_connection_id", None)

        if not business_connection_id:
            # не бизнес-апдейт, просто пробрасываем
            return await handler(event, data)
        
        # 1. Получаем user_id
        if isinstance(event, Message):
            user_telegram_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_telegram_id = event.from_user.id
        else:
            # Если вдруг другой тип события — просто пробрасываем дальше
            return await handler(event, data)

        redis_key = (
            f"{constants.REDIS_KEY_OLD_USERS}:{business_connection_id}:old_users_telegram_ids"
        )

        is_old = await self.redis.sismember(redis_key, user_telegram_id)
        if is_old:
            return  # просто игнорируем сообщение от юзера(если он старый и уже писал)

        return await handler(event, data)