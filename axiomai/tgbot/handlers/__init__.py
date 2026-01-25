from aiogram import Dispatcher

from axiomai.tgbot.handlers import (
    start,
    create_cashback_table,
    link_business_account,
    process_clients,
    my_cabinet,
    exception,
    buy_leads,
    admin_confirms,
)


def setup(dispatcher: Dispatcher) -> None:
    dispatcher.include_routers(
        exception.router,
        link_business_account.router,
        create_cashback_table.router,
        process_clients.router,
        my_cabinet.router,
        buy_leads.router,
        admin_confirms.router,
        start.router,
    )
