from aiogram import Dispatcher

from axiomai.tgbot.handlers import (
    admin_confirms,
    buy_leads,
    create_cashback_table,
    exception,
    link_business_account,
    my_cabinet,
    process_clients,
    start,
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
