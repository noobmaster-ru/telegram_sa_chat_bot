import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dishka import make_async_container, AsyncContainer

from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.config import load_config, Config
from axiomai.infrastructure.di import DatabaseProvider, GatewaysProvider, ObserverInteractorsProvider
from axiomai.infrastructure.logging import setup_logging


logger = logging.getLogger(__name__)


async def run_cashback_tables_observer(di_container: AsyncContainer) -> None:
    logger.info("start cashback tables observering...")
    while True:
        async with di_container() as r_container:
            observe_cashback_tables = await r_container.get(ObserveCashbackTables)
            await observe_cashback_tables.execute()

        await asyncio.sleep(10)


async def main() -> None:
    config = load_config()
    setup_logging(json_logs=config.json_logs)
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    di_container = make_async_container(
        DatabaseProvider(),
        ObserverInteractorsProvider(),
        GatewaysProvider(),
        context={Config: config, Bot: bot},
    )
    try:
        await run_cashback_tables_observer(di_container)
    finally:
        await di_container.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("subscription observer stopped")
