import logging
from decimal import Decimal

from aiogram import Bot

from axiomai.constants import OWNER_TELEGRAM_ID
from axiomai.infrastructure.database.gateways.balance_notification import BalanceNotificationGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)

THRESHOLDS = [Decimal("0.50"), Decimal("0.10"), Decimal("0.01")]


class ObserveBalanceNotifications:
    def __init__(
        self,
        cabinet_gateway: CabinetGateway,
        user_gateway: UserGateway,
        balance_notification_gateway: BalanceNotificationGateway,
        transaction_manager: TransactionManager,
        bot: Bot,
    ) -> None:
        self._cabinet_gateway = cabinet_gateway
        self._user_gateway = user_gateway
        self._balance_notification_gateway = balance_notification_gateway
        self._transaction_manager = transaction_manager
        self._bot = bot

    async def execute(self) -> None:
        cabinets = await self._cabinet_gateway.get_cabinets_with_low_balance()

        for cabinet in cabinets:
            user = await self._user_gateway.get_user_by_cabinet_id(cabinet.id)
            if not user or not user.telegram_id:
                user_id_val = user.id if user else "Unknown"
                logger.warning("user.id=%s not found for cabinet_id=%s", user_id_val, cabinet.id)
                continue

            sent_thresholds = await self._balance_notification_gateway.get_sent_thresholds(
                cabinet.id, cabinet.initial_balance
            )

            for threshold in THRESHOLDS:
                if threshold in sent_thresholds:
                    continue

                threshold_amount = int(cabinet.initial_balance * threshold)
                if cabinet.balance <= threshold_amount:
                    await self._balance_notification_gateway.create_notification(
                        cabinet_id=cabinet.id,
                        initial_balance=cabinet.initial_balance,
                        threshold=threshold,
                    )
                    await self._transaction_manager.commit()

                    await self._send_notification(user.telegram_id, cabinet.balance)
                    if user.telegram_id != OWNER_TELEGRAM_ID:
                        await self._send_notification(OWNER_TELEGRAM_ID, cabinet.balance, seller_telegram_id=user.telegram_id)
                    logger.info("sent balance notification for cabinet_id=%s, threshold=%s", cabinet.id, threshold)

    async def _send_notification(self, telegram_id: int, balance: int, seller_telegram_id: int | None = None) -> None:
        if seller_telegram_id:
            text = (
                f"📋 Уведомление для селлера <code>{seller_telegram_id}</code>:\n\n"
                f"⚠️ Внимание! На балансе осталось {balance} ₽ для выплат кэшбека.\n\n"
                "Нужно пополнить баланс."
            )
        else:
            text = (
                f"⚠️ Внимание! На вашем балансе осталось {balance} ₽ для выплат кэшбека.\n\n"
                "Пополните баланс, чтобы не останавливать обработку заявок."
            )
        await self._bot.send_message(chat_id=telegram_id, text=text)
