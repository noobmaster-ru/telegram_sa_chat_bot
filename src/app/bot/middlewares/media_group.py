import asyncio
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message, ContentType


class MediaGroupMiddleware(BaseMiddleware):
    album_data: Dict[str, List[Message]] = {}

    def __init__(self, latency: int = 0.3):
        """
        :param latency: Задержка в секундах для сбора всех сообщений медиагруппы.
        """
        self.latency = latency
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        
        # Если это не фото и не видео, просто пропускаем
        if event.content_type not in (ContentType.PHOTO, ContentType.VIDEO):
            return await handler(event, data)

        # Если media_group_id нет (одиночное фото), пропускаем обычному хэндлеру
        if event.media_group_id is None:
            return await handler(event, data)

        # Собираем сообщения в словарь альбомов
        try:
            self.album_data[event.media_group_id].append(event)
        except KeyError:
            self.album_data[event.media_group_id] = [event]
            await asyncio.sleep(self.latency)
            messages = self.album_data.pop(event.media_group_id)
            
            # Если в альбоме только одно сообщение, 
            # обрабатываем его как обычное одиночное сообщение
            if len(messages) == 1:
                 return await handler(messages[0], data)
            
            # Иначе, передаем весь список сообщений в хэндлер через ключ "album"
            data["album"] = messages
            return await handler(event, data)