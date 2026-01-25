from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from redis.asyncio import Redis

from axiomai.infrastructure.message_debouncer import (
    MessageDebouncer,
    MessageData,
    merge_messages_text,
)


class TestMessageFiltering:
    """Тесты фильтрации бессодержательных сообщений"""

    def setup_method(self):
        """Создаем debouncer для каждого теста"""
        redis_mock = MagicMock(spec=Redis)
        self.debouncer = MessageDebouncer(redis=redis_mock, delay_seconds=1)

    def test_filter_greeting_hello(self):
        """Приветствие 'Здравствуйте' должно быть отфильтровано"""
        assert not self.debouncer._is_meaningful_message("Здравствуйте")
        assert not self.debouncer._is_meaningful_message("здравствуйте")
        assert not self.debouncer._is_meaningful_message("ЗДРАВСТВУЙТЕ!")

    def test_filter_greeting_privet(self):
        """Приветствие 'Привет' должно быть отфильтровано"""
        assert not self.debouncer._is_meaningful_message("Привет")
        assert not self.debouncer._is_meaningful_message("привет")
        assert not self.debouncer._is_meaningful_message("Привет!")

    def test_filter_greeting_dobriy_den(self):
        """Приветствие 'Добрый день' должно быть отфильтровано"""
        assert not self.debouncer._is_meaningful_message("Добрый день")
        assert not self.debouncer._is_meaningful_message("доброе утро")
        assert not self.debouncer._is_meaningful_message("Добрый вечер!")

    def test_filter_greeting_english(self):
        """Английские приветствия должны быть отфильтрованы"""
        assert not self.debouncer._is_meaningful_message("hello")
        assert not self.debouncer._is_meaningful_message("Hello!")
        assert not self.debouncer._is_meaningful_message("Hi")
        assert not self.debouncer._is_meaningful_message("Hey")

    def test_filter_very_short_messages(self):
        """Очень короткие сообщения должны быть отфильтрованы"""
        assert not self.debouncer._is_meaningful_message("ок")
        assert not self.debouncer._is_meaningful_message("да")
        assert not self.debouncer._is_meaningful_message("нет")
        assert not self.debouncer._is_meaningful_message("!")
        assert not self.debouncer._is_meaningful_message("???")

    def test_filter_emoji_only(self):
        """Сообщения только с emoji должны быть отфильтрованы"""
        assert not self.debouncer._is_meaningful_message("👍")
        assert not self.debouncer._is_meaningful_message("😊😊")
        assert not self.debouncer._is_meaningful_message("🔥🔥🔥")

    def test_filter_punctuation_only(self):
        """Сообщения только со знаками препинания должны быть отфильтрованы"""
        assert not self.debouncer._is_meaningful_message("...")
        assert not self.debouncer._is_meaningful_message("!!!")
        assert not self.debouncer._is_meaningful_message("???")
        assert not self.debouncer._is_meaningful_message("!?!?")

    def test_filter_empty_messages(self):
        """Пустые сообщения должны быть отфильтрованы"""
        assert not self.debouncer._is_meaningful_message("")
        assert not self.debouncer._is_meaningful_message("   ")
        assert not self.debouncer._is_meaningful_message("\n\n")
        assert not self.debouncer._is_meaningful_message(None)

    def test_allow_meaningful_messages(self):
        """Содержательные сообщения должны проходить фильтр"""
        assert self.debouncer._is_meaningful_message("Я по поводу ролика")
        assert self.debouncer._is_meaningful_message("можно ли инструкцию")
        assert self.debouncer._is_meaningful_message("Хочу узнать про кешбек")
        assert self.debouncer._is_meaningful_message("Есть вопрос по товару")

    def test_allow_long_enough_messages(self):
        """Сообщения длиннее 3 символов должны проходить"""
        assert self.debouncer._is_meaningful_message("Как дела?")
        assert self.debouncer._is_meaningful_message("Хорошо")
        assert self.debouncer._is_meaningful_message("Спасибо")

    def test_allow_messages_with_emoji_and_text(self):
        """Сообщения с emoji и текстом должны проходить"""
        assert self.debouncer._is_meaningful_message("Спасибо 👍")
        assert self.debouncer._is_meaningful_message("😊 Хорошо")
        assert self.debouncer._is_meaningful_message("Отлично 🔥 работает")


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

    debouncer = MessageDebouncer(redis=redis_mock, immediate_processing_length=100)

    process_callback = AsyncMock()

    long_text = "a" * 150  # Сообщение длиннее порога
    message_data = MessageData(
        text=long_text,
        timestamp=datetime.now().timestamp(),
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
