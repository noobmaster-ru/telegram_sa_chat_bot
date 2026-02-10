import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.models.buyer import Buyer
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)

INACTIVE_HOURS = 48


class ObserveInactiveReminders:
    def __init__(
        self,
        buyer_gateway: BuyerGateway,
        cabinet_gateway: CabinetGateway,
        transaction_manager: TransactionManager,
        bot: Bot,
    ) -> None:
        self._buyer_gateway = buyer_gateway
        self._cabinet_gateway = cabinet_gateway
        self._transaction_manager = transaction_manager
        self._bot = bot

    async def execute(self) -> None:
        inactive_since = datetime.now(UTC) - timedelta(hours=INACTIVE_HOURS)
        buyers = await self._buyer_gateway.get_inactive_buyers(inactive_since)

        for buyer in buyers:
            reminder_text = _get_reminder_text(buyer)
            if not reminder_text:
                continue

            cabinet = await self._cabinet_gateway.get_cabinet_by_id(buyer.cabinet_id)
            business_connection_id = cabinet.business_connection_id if cabinet else None

            try:
                await self._bot.send_message(
                    chat_id=buyer.telegram_id,
                    text=reminder_text,
                    business_connection_id=business_connection_id,
                )
                logger.info("sent reminder to buyer_id=%s, telegram_id=%s", buyer.id, buyer.telegram_id)
            except TelegramForbiddenError:
                logger.warning("user blocked bot: buyer_id=%s, telegram_id=%s", buyer.id, buyer.telegram_id)
            except Exception:
                logger.exception("failed to send reminder to buyer_id=%s", buyer.id)
                continue

            buyer.updated_at = datetime.now(UTC)
            await self._transaction_manager.commit()


def _get_reminder_text(buyer: Buyer) -> str | None:  # noqa: PLR0911
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
