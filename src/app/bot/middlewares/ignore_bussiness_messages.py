from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from src.core.config import constants
from redis.asyncio import Redis

class IgnoreBusinessMessagesMiddleware(BaseMiddleware):
    def __init__(
        self, 
        redis_client: Redis
    ):
        super().__init__()        
        self.redis = redis_client
        self.key = constants.REDIS_KEY_BUSINESS_ACCOUNTS_IDS

    
    async def __call__(
        self,
        handler: Callable[[Dict[str, Any], Any], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        
        # проверяем, является ли этот user.id бизнес-аккаунтом / менеджером
        is_business = await self.redis.sismember(self.key, user.id)
        if is_business:
            # просто игнорируем сообщение
            return
        
        return await handler(event, data)
        
        # if user and user.id in constants.BUSINESS_ACCOUNTS_IDS:
        #     return  # просто игнорируем сообщение от бизнес аккаунта(если менеджер будет писать)
        # return await handler(event, data)