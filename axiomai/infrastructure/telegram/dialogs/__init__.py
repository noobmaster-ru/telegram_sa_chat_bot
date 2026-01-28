from aiogram import Dispatcher, Router

from axiomai.infrastructure.telegram.dialogs.buy_leads import buy_leads_dialog
from axiomai.infrastructure.telegram.dialogs.cashback_article.dialog import cashback_article_dialog
from axiomai.infrastructure.telegram.dialogs.create_cashback_table import create_cashback_table_dialog
from axiomai.infrastructure.telegram.dialogs.my_cabinet import my_cabinet_dialog
from axiomai.tgbot.filters.ignore_self_message import SelfBusinessMessageFilter


def setup(dispatcher: Dispatcher) -> None:
    router = Router()

    router.business_message.filter(~SelfBusinessMessageFilter())

    router.include_routers(create_cashback_table_dialog, my_cabinet_dialog, cashback_article_dialog, buy_leads_dialog)

    dispatcher.include_router(router)
