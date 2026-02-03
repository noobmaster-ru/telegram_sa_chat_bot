import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from redis.asyncio import Redis

from axiomai.config import MessageDebouncerConfig

logger = logging.getLogger(__name__)


@dataclass
class MessageData:
    """Данные одного сообщения для накопления"""

    text: str | None
    timestamp: float
    message_id: int
    has_photo: bool
    photo_url: str | None = None
    chat_id: int | None = None  # Добавлено для возможности отправки ответа


@dataclass
class AccumulatedMessages:
    """Накопленные сообщения для обработки"""

    messages: list[MessageData]
    timer_id: str
    scheduled_at: float


class MessageDebouncer:
    """
    Сервис для накопления нескольких коротких сообщений от пользователей
    и их обработки как единого запроса после паузы.

    Использует Redis для временного хранения и asyncio для управления таймерами.
    """

    def __init__(self, redis: Redis, config: MessageDebouncerConfig) -> None:
        self.redis = redis
        self.delay_seconds = config.message_debounce_delay
        self.ttl_seconds = config.message_accumulation_ttl
        self.immediate_processing_length = config.immediate_processing_length
        self._active_timers: dict[str, asyncio.Task] = {}

    async def add_message(
        self,
        business_connection_id: str,
        chat_id: int,
        message_data: MessageData,
        process_callback: Callable[[str, int, list[MessageData]], Awaitable[None]],
    ) -> None:
        """Добавляет сообщение в очередь накопления и запускает/перезапускает таймер"""
        redis_key = _get_redis_key(business_connection_id, chat_id)
        timer_key = f"{business_connection_id}:{chat_id}"

        # Если сообщение очень длинное - обрабатываем немедленно
        if message_data.text and len(message_data.text) >= self.immediate_processing_length:
            logger.info("processing long message immediately (length: %s)", len(message_data.text))
            await process_callback(business_connection_id, chat_id, [message_data])
            return

        # Получаем текущие накопленные сообщения
        existing_data = await self.redis.get(redis_key)

        if existing_data:
            accumulated = _deserialize_messages(existing_data)
        else:
            accumulated = AccumulatedMessages(
                messages=[], timer_id=timer_key, scheduled_at=datetime.now(UTC).timestamp()
            )

        accumulated.messages.append(message_data)
        accumulated.scheduled_at = datetime.now(UTC).timestamp() + self.delay_seconds

        serialized = _serialize_messages(accumulated)
        await self.redis.setex(redis_key, self.ttl_seconds, serialized)

        logger.info("added message to accumulation buffer. chat: %s, total: %s", chat_id, len(accumulated.messages))

        # Отменяем старый таймер если есть
        if timer_key in self._active_timers:
            old_timer = self._active_timers[timer_key]
            if not old_timer.done():
                old_timer.cancel()
                logger.debug("cancelled previous timer for chat %s", chat_id)

        # Запускаем новый таймер
        timer_task = asyncio.create_task(
            self._delayed_process(business_connection_id, chat_id, process_callback, self.delay_seconds)
        )
        self._active_timers[timer_key] = timer_task

        logger.debug("started new timer for chat %s (%ss)", chat_id, self.delay_seconds)

    async def _delayed_process(
        self,
        business_connection_id: str,
        chat_id: int,
        process_callback: Callable[[str, int, list[MessageData]], Awaitable[None]],
        delay: float,
    ) -> None:
        """Ожидает паузу и затем обрабатывает накопленные сообщения"""
        try:
            await asyncio.sleep(delay)

            redis_key = _get_redis_key(business_connection_id, chat_id)
            timer_key = f"{business_connection_id}:{chat_id}"

            # Получаем накопленные сообщения
            data = await self.redis.get(redis_key)
            if not data:
                logger.warning("no accumulated messages found for chat %s", chat_id)
                return

            accumulated = _deserialize_messages(data)

            logger.info("processing accumulated messages. chat: %s, total: %s", chat_id, len(accumulated.messages))

            await self.redis.delete(redis_key)
            if timer_key in self._active_timers:
                del self._active_timers[timer_key]

            try:
                await process_callback(business_connection_id, chat_id, accumulated.messages)
            except Exception as e:
                logger.exception("error processing accumulated messages", exc_info=e)

        except asyncio.CancelledError:
            logger.debug("timer cancelled for chat %s", chat_id)
            raise
        except Exception as e:
            logger.exception("error in delayed processing: %s", exc_info=e)


def _get_redis_key(business_connection_id: str, chat_id: int) -> str:
    """Генерация ключа Redis для уникального чата"""
    return f"pending_messages:{business_connection_id}:{chat_id}"


def _serialize_messages(accumulated: AccumulatedMessages) -> str:
    """Сериализация накопленных сообщений в JSON"""
    return json.dumps(
        {
            "messages": [
                {
                    "text": msg.text,
                    "timestamp": msg.timestamp,
                    "message_id": msg.message_id,
                    "has_photo": msg.has_photo,
                    "photo_url": msg.photo_url,
                }
                for msg in accumulated.messages
            ],
            "timer_id": accumulated.timer_id,
            "scheduled_at": accumulated.scheduled_at,
        }
    )


def _deserialize_messages(data: bytes | str) -> AccumulatedMessages:
    """Десериализация накопленных сообщений из JSON"""
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    parsed = json.loads(data)
    return AccumulatedMessages(
        messages=[
            MessageData(
                text=msg["text"],
                timestamp=msg["timestamp"],
                message_id=msg["message_id"],
                has_photo=msg["has_photo"],
                photo_url=msg.get("photo_url"),
            )
            for msg in parsed["messages"]
        ],
        timer_id=parsed["timer_id"],
        scheduled_at=parsed["scheduled_at"],
    )


def merge_messages_text(messages: list[MessageData]) -> str:
    """Объединяет текст из нескольких сообщений в единую строку"""
    texts = [msg.text for msg in messages if msg.text]
    return " ".join(texts).strip()
