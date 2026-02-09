import logging

from aiogram import Bot

from axiomai.application.exceptions.cashback_table import WritePermissionError
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.google_sheets import GoogleSheetsGateway
from axiomai.infrastructure.telegram.keyboards.reply import get_kb_menu

logger = logging.getLogger(__name__)


class ObserveCashbackTables:
    def __init__(
        self,
        user_gateway: UserGateway,
        cashback_table_gateway: CashbackTableGateway,
        cabinet_gateway: CabinetGateway,
        google_sheets_gateway: GoogleSheetsGateway,
        transaction_manager: TransactionManager,
        bot: Bot,
    ) -> None:
        self._user_gateway = user_gateway
        self._cashback_table_gateway = cashback_table_gateway
        self._cabinet_gateway = cabinet_gateway
        self._google_sheets_gateway = google_sheets_gateway
        self._transaction_manager = transaction_manager
        self._bot = bot

    async def execute(self) -> None:
        tables = await self._cashback_table_gateway.get_new_cashback_tables()

        for table in tables:
            user = await self._user_gateway.get_user_by_cabinet_id(table.cabinet_id)
            if not user:
                logger.error("user telegram_id = %s, not found for cabinet_id=%s", user.telegram_id, table.cabinet_id)
                continue

            try:
                await self._google_sheets_gateway.ensure_service_account_added(table.table_id)
            except PermissionError:
                continue
            except WritePermissionError:
                if table.status == CashbackTableStatus.NEW:
                    await self._bot.send_message(
                        chat_id=user.telegram_id,
                        text=(
                            "✅ Мы увидели что вы добавили наш сервисный аккаунт, но у него нет прав на редактирование вашей таблицы. "
                            "Пожалуйста, предоставьте права на редактирование и мы продолжим настройку."
                        ),
                    )
                    table.status = CashbackTableStatus.WAITING_WRITE_PERMISSION
                    await self._transaction_manager.commit()
                continue

            table.status = CashbackTableStatus.VERIFIED
            await self._transaction_manager.commit()

            cabinet = await self._cabinet_gateway.get_cabinet_by_id(table.cabinet_id)
            if not cabinet or not cabinet.link_code:
                logger.error("cabinet or link_code not found for cabinet_id=%s", table.cabinet_id)
                continue

            bot_username = (await self._bot.me()).username
            link_url = f"https://t.me/{bot_username}?start=link_{cabinet.link_code}"

            await self._bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    "✅ Таблица кешбэка успешно настроена и готова к работе!\n\n"
                    "Теперь вам нужно подключить ваш бизнес-аккаунт Telegram к кабинету.\n\n"
                    "Для этого перейдите по этой ссылке, <b>с бизнес-аккаунта, который вы собираетесь использовать для раздачи</b>:\n"
                    f"{link_url}\n\n"
                    "После подключения, бот сможет автоматически будет обрабатывать сообщения от клиентов."
                ),
                reply_markup=get_kb_menu(cabinet),
            )

            logger.info("table %s verified successfully", table.table_id)
