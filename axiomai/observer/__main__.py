import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dishka import AsyncContainer, make_async_container

from axiomai.application.interactors.observe_balance_notifications import ObserveBalanceNotifications
from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.application.interactors.observe_inactive_reminders import ObserveInactiveReminders
from axiomai.application.interactors.sync_cashback_tables import SyncCashbackTables
from axiomai.config import Config, load_config
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


async def run_sync_cashback_tables(di_container: AsyncContainer) -> None:
    logger.info("start sync cashback tables...")
    while True:
        async with di_container() as r_container:
            sync_cashback_tables = await r_container.get(SyncCashbackTables)
            await sync_cashback_tables.execute()

        await asyncio.sleep(10)


async def run_balance_notifications_observer(di_container: AsyncContainer) -> None:
    logger.info("start balance notifications observer...")
    while True:
        async with di_container() as r_container:
            observe_balance_notifications = await r_container.get(ObserveBalanceNotifications)
            await observe_balance_notifications.execute()

        await asyncio.sleep(10)


async def run_inactive_reminders_observer(di_container: AsyncContainer) -> None:
    logger.info("start inactive reminders observer...")
    while True:
        async with di_container() as r_container:
            observe_inactive_reminders = await r_container.get(ObserveInactiveReminders)
            await observe_inactive_reminders.execute()

        await asyncio.sleep(3600)  # Проверяем раз в час


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
        await asyncio.gather(
            asyncio.create_task(run_cashback_tables_observer(di_container)),
            asyncio.create_task(run_sync_cashback_tables(di_container)),
            asyncio.create_task(run_balance_notifications_observer(di_container)),
            asyncio.create_task(run_inactive_reminders_observer(di_container)),
        )
    finally:
        await di_container.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("observer stopped")
