import logging
from datetime import datetime, UTC, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.models.buyer import Buyer
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)

INACTIVE_HOURS = 48


class ObserveInactiveReminders:
    def __init__(
        self,
        buyer_gateway: BuyerGateway,
        transaction_manager: TransactionManager,
        bot: Bot,
    ) -> None:
        self._buyer_gateway = buyer_gateway
        self._transaction_manager = transaction_manager
        self._bot = bot

    async def execute(self) -> None:
        inactive_since = datetime.now(UTC) - timedelta(hours=INACTIVE_HOURS)
        buyers = await self._buyer_gateway.get_inactive_buyers(inactive_since)

        for buyer in buyers:
            reminder_text = _get_reminder_text(buyer)
            if not reminder_text:
                continue

            try:
                await self._bot.send_message(chat_id=buyer.telegram_id, text=reminder_text)
                logger.info("sent reminder to buyer_id=%s, telegram_id=%s", buyer.id, buyer.telegram_id)
            except TelegramForbiddenError:
                logger.warning("user blocked bot: buyer_id=%s, telegram_id=%s", buyer.id, buyer.telegram_id)
            except Exception:
                logger.exception("failed to send reminder to buyer_id=%s", buyer.id)
                continue

            buyer.updated_at = datetime.now(UTC)
            await self._transaction_manager.commit()


def _get_reminder_text(buyer: Buyer) -> str | None:
    """Определяет текст напоминания в зависимости от состояния покупателя."""
    if not buyer.is_ordered:
        return "⏰ Ждём скриншот вашего заказа"

    if not buyer.is_left_feedback:
        return "⏰ Ждём скриншот вашего отзыва"

    if not buyer.is_cut_labels:
        return "⏰ Ждём фото разрезанных этикеток"

    if not buyer.phone_number:
        return "⏰ Ждём ваш номер телефона для выплаты"

    if not buyer.bank:
        return "⏰ Ждём название банка для выплаты"

    if not buyer.amount:
        return "⏰ Ждём подтверждение реквизитов"

    return None
