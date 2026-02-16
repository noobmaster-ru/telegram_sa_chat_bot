import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage, DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram_dialog import setup_dialogs
from aiogram_dialog.widgets.text import setup_jinja
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka
from redis.asyncio import Redis

from axiomai.config import Config, load_config
from axiomai.infrastructure.di import ConfigProvider, DatabaseProvider, GatewaysProvider, TgbotInteractorsProvider
from axiomai.infrastructure.logging import setup_logging
from axiomai.infrastructure.telegram import dialogs
from axiomai.tgbot import bot_commands, handlers


async def main() -> None:
    config = load_config()
    setup_logging(json_logs=config.json_logs)

    redis = Redis.from_url(config.redis_uri)
    storage = RedisStorage(redis, key_builder=DefaultKeyBuilder(with_destiny=True, with_business_connection_id=True))

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = Dispatcher(storage=storage)

    # Создаем DI контейнер с провайдерами
    di_container = make_async_container(
        ConfigProvider(),
        DatabaseProvider(),
        TgbotInteractorsProvider(),
        GatewaysProvider(),
        context={Config: config, Redis: redis, Bot: bot, BaseStorage: storage},
    )

    handlers.setup(dispatcher)
    dialogs.setup(dispatcher)

    setup_jinja(dispatcher)
    setup_dialogs(dispatcher)
    setup_dishka(di_container, dispatcher)

    try:
        await bot_commands.setup(bot)
        await dispatcher.start_polling(bot, di_container=di_container)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
