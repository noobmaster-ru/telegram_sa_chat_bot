from aiogram import Dispatcher

from axiomai.tgbot.handlers import (
    admin_confirms,
    auto_payments,
    buy_leads,
    confirm_screenshots,
    create_cashback_table,
    exception,
    link_business_account,
    my_cabinet,
    process_clients,
    refill_balance,
    start,
)


def setup(dispatcher: Dispatcher) -> None:
    dispatcher.include_routers(
        exception.router,
        link_business_account.router,
        create_cashback_table.router,
        confirm_screenshots.router,
        process_clients.router,
        my_cabinet.router,
        buy_leads.router,
        refill_balance.router,
        auto_payments.router,
        admin_confirms.router,
        start.router,
    )
