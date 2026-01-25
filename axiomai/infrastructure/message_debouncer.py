import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Awaitable

from redis.asyncio import Redis

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

    # Фильтр бессодержательных сообщений
    GREETING_PATTERNS = [
        r"^(привет|здравствуй(те)?|добр(ый|ого|ое|ая)\s*(день|утро|вечер)|hi|hello|hey)[\s!.]*$",
        r"^(хай|йоу|салам|хеллоу)[\s!.]*$",
    ]

    def __init__(
        self,
        redis: Redis,
        delay_seconds: int = 1,
        ttl_seconds: int = 300,
        immediate_processing_length: int = 500,
    ):
        """
        Инициализация debouncer

        Args:
            redis: Redis клиент для хранения
            delay_seconds: Сколько секунд ждать паузы перед обработкой
            ttl_seconds: TTL для накопленных сообщений в Redis (автоочистка)
            immediate_processing_length: Длина сообщения для немедленной обработки
        """
        self.redis = redis
        self.delay_seconds = delay_seconds
        self.ttl_seconds = ttl_seconds
        self.immediate_processing_length = immediate_processing_length
        self._active_timers: dict[str, asyncio.Task] = {}
        self._greeting_regex = re.compile("|".join(self.GREETING_PATTERNS), re.IGNORECASE | re.UNICODE)

    def _is_meaningful_message(self, text: str | None) -> bool:
        """
        Проверяет, является ли сообщение содержательным

        Фильтрует:
        - Приветствия (Здравствуйте, Привет, Hello и т.д.)
        - Очень короткие сообщения (< 3 символов без emoji)
        - Только emoji без текста
        - Только знаки препинания
        """
        if not text:
            return False

        text = text.strip()

        # Пустые сообщения
        if not text:
            return False

        # Приветствия
        if self._greeting_regex.match(text):
            logger.debug("filtered greeting message: %s", text)
            return False

        # Удаляем emoji и проверяем что осталось
        text_without_emoji = re.sub(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]+",
            "",
            text,
        )
        text_without_emoji = text_without_emoji.strip()

        # Только emoji без текста
        if not text_without_emoji:
            logger.debug("filtered emoji-only message: %s", text)
            return False

        # Только знаки препинания
        if re.match(r"^[^\w\s]+$", text_without_emoji, re.UNICODE):
            logger.debug("filtered punctuation-only message: %s", text)
            return False

        # Очень короткие (менее 3 символов)
        if len(text_without_emoji) <= 3:
            logger.debug("filtered short message: %s", text)
            return False

        return True

    async def add_message(
        self,
        business_connection_id: str,
        chat_id: int,
        message_data: MessageData,
        process_callback: Callable[[str, int, list[MessageData]], Awaitable[None]],
    ) -> None:
        """
        Добавляет сообщение в очередь накопления и запускает/перезапускает таймер

        Args:
            business_connection_id: ID бизнес-подключения
            chat_id: ID чата клиента
            message_data: Данные сообщения
            process_callback: Функция для обработки накопленных сообщений
        """
        redis_key = _get_redis_key(business_connection_id, chat_id)
        timer_key = f"{business_connection_id}:{chat_id}"

        # Если сообщение очень длинное - обрабатываем немедленно
        if message_data.text and len(message_data.text) >= self.immediate_processing_length:
            logger.info("processing long message immediately (length: %s)", len(message_data.text))
            await process_callback(business_connection_id, chat_id, [message_data])
            return

        # Если есть фото - всегда считаем содержательным
        is_meaningful = message_data.has_photo or self._is_meaningful_message(message_data.text)

        # Получаем текущие накопленные сообщения
        existing_data = await self.redis.get(redis_key)

        if existing_data:
            accumulated = _deserialize_messages(existing_data)
        else:
            accumulated = AccumulatedMessages(messages=[], timer_id=timer_key, scheduled_at=datetime.now().timestamp())

        accumulated.messages.append(message_data)
        accumulated.scheduled_at = datetime.now().timestamp() + self.delay_seconds

        serialized = _serialize_messages(accumulated)
        await self.redis.setex(redis_key, self.ttl_seconds, serialized)

        logger.info(
            "added message to accumulation buffer. chat: %s, total: %s, meaningful: %s",
            chat_id,
            len(accumulated.messages),
            is_meaningful,
        )

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
        """
        Ожидает паузу и затем обрабатывает накопленные сообщения
        """
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

            # Фильтруем бессодержательные сообщения
            meaningful_messages = [
                msg for msg in accumulated.messages if msg.has_photo or self._is_meaningful_message(msg.text)
            ]

            logger.info(
                "processing accumulated messages. chat: %s, total: %s, meaningful: %s",
                chat_id,
                len(accumulated.messages),
                len(meaningful_messages),
            )

            # Если после фильтрации ничего не осталось - не обрабатываем
            if not meaningful_messages:
                logger.info("no meaningful messages to process for chat %s", chat_id)
                await self.redis.delete(redis_key)
                return

            # Обрабатываем накопленные сообщения
            try:
                await process_callback(business_connection_id, chat_id, meaningful_messages)
            except Exception as e:
                logger.error("error processing accumulated messages", exc_info=e)
            finally:
                # Очищаем Redis и таймер
                await self.redis.delete(redis_key)
                if timer_key in self._active_timers:
                    del self._active_timers[timer_key]

        except asyncio.CancelledError:
            logger.debug("timer cancelled for chat %s", chat_id)
            raise
        except Exception as e:
            logger.error("error in delayed processing: %s", exc_info=e)


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
    """
    Объединяет текст из нескольких сообщений в единую строку
    """
    texts = [msg.text for msg in messages if msg.text]
    return " ".join(texts).strip()
