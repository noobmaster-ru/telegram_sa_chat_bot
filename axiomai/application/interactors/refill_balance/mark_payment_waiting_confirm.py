import logging

from aiogram import Bot

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.application.exceptions.payment import PaymentAlreadyProcessedError, PaymentNotFoundError
from axiomai.config import Config
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.models.payment import PaymentStatus
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.keyboards.inline import build_payment_admin_keyboard

logger = logging.getLogger(__name__)


class MarkRefillBalancePaymentWaitingConfirm:
    def __init__(
        self,
        tm: TransactionManager,
        payment_gateway: PaymentGateway,
        cabinet_gateway: CabinetGateway,
        config: Config,
        bot: Bot,
    ) -> None:
        self._tm = tm
        self._payment_gateway = payment_gateway
        self._cabinet_gateway = cabinet_gateway
        self._config = config
        self._bot = bot

    async def execute(self, payment_id: int) -> None:
        payment = await self._payment_gateway.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundError(f"Payment with id {payment_id} not found")

        if payment.status != PaymentStatus.CREATED:
            raise PaymentAlreadyProcessedError(
                f"Payment with id {payment_id} cannot be marked as waiting (status: {payment.status.value})"
            )

        payment.status = PaymentStatus.WAITING_CONFIRM

        await self._tm.commit()

        admin_chat_id = self._config.admin_telegram_ids[0]
        cabinet = await self._cabinet_gateway.get_cabinet_by_cashback_table_id(payment.cashback_table_id)
        if not cabinet:
            raise CabinetNotFoundError(
                f"Cabinet by cashback_table_id = {payment.cashback_table_id} not found for mark waiting"
            )

        text = (
            f"💸 Новое пополнение баланса {payment_id}\n"
            f"Кабинет ID: {cabinet.id}\n"
            f"Сумма: {payment.amount} ₽\n\n"
            "Подтвердите, пожалуйста"
        )

        await self._bot.send_message(
            chat_id=admin_chat_id,
            text=text,
            reply_markup=build_payment_admin_keyboard(payment_id),
        )

        logger.info("refill balance payment %s marked as waiting confirmation", payment_id)
