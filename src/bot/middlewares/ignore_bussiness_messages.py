from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from src.core.config import constants


class IgnoreBusinessMessagesMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Dict[str, Any], Any], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if user and user.id in constants.BUSINESS_ACCOUNTS_IDS:
            return  # просто игнорируем сообщение от бизнес аккаунта(если менеджер будет писать)
        return await handler(event, data)