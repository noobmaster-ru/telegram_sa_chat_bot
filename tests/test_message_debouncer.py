from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from redis.asyncio import Redis

from axiomai.config import MessageDebouncerConfig
from axiomai.infrastructure.message_debouncer import (
    MessageDebouncer,
    MessageData,
    merge_messages_text,
)


class TestMessageMerging:
    """Тесты объединения сообщений"""

    def test_merge_multiple_messages(self):
        """Объединение нескольких сообщений в один текст"""
        messages = [
            MessageData(text="Я по поводу", timestamp=1.0, message_id=1, has_photo=False),
            MessageData(text="ролика", timestamp=2.0, message_id=2, has_photo=False),
            MessageData(text="можно инструкцию", timestamp=3.0, message_id=3, has_photo=False),
        ]

        merged = merge_messages_text(messages)
        assert merged == "Я по поводу ролика можно инструкцию"

    def test_merge_messages_with_none(self):
        """Игнорирование None при объединении"""
        messages = [
            MessageData(text="Первое", timestamp=1.0, message_id=1, has_photo=False),
            MessageData(text=None, timestamp=2.0, message_id=2, has_photo=True),
            MessageData(text="Второе", timestamp=3.0, message_id=3, has_photo=False),
        ]

        merged = merge_messages_text(messages)
        assert merged == "Первое Второе"

    def test_merge_empty_messages(self):
        """Объединение пустых сообщений"""
        messages = [
            MessageData(text=None, timestamp=1.0, message_id=1, has_photo=True),
            MessageData(text="", timestamp=2.0, message_id=2, has_photo=False),
        ]

        merged = merge_messages_text(messages)
        assert merged == ""


async def test_immediate_processing_for_long_messages():
    """Длинные сообщения должны обрабатываться немедленно"""
    redis_mock = MagicMock(spec=Redis)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()

    debouncer = MessageDebouncer(redis=redis_mock, config=MessageDebouncerConfig(IMMEDIATE_PROCESSING_LENGTH=100))

    process_callback = AsyncMock()

    long_text = "a" * 150  # Сообщение длиннее порога
    message_data = MessageData(
        text=long_text,
        timestamp=datetime.now(timezone.utc).timestamp(),
        message_id=1,
        has_photo=False,
    )

    await debouncer.add_message(
        business_connection_id="biz_1",
        chat_id=100,
        message_data=message_data,
        process_callback=process_callback,
    )

    process_callback.assert_called_once()
    redis_mock.setex.assert_not_called()
