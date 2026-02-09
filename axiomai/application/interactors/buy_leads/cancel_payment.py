import logging

from axiomai.application.exceptions.payment import PaymentAlreadyProcessedError, PaymentNotFoundError
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.models.payment import PaymentStatus
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class CancelBuyLeadsPayment:
    def __init__(
        self,
        tm: TransactionManager,
        payment_gateway: PaymentGateway,
    ) -> None:
        self._tm = tm
        self._payment_gateway = payment_gateway

    async def execute(self, admin_telegram_id: int, payment_id: int, reason: str | None = None) -> None:
        payment = await self._payment_gateway.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundError(f"Payment with id = {payment_id} not found")

        if payment.status != PaymentStatus.WAITING_CONFIRM:
            raise PaymentAlreadyProcessedError(
                f"Payment with id = {payment_id} has already been processed (status: {payment.status.value})"
            )

        payment.status = PaymentStatus.CANCELED
        if reason:
            payment.canceled_reason = reason

        await self._tm.commit()

        logger.info("buy leads payment %s canceled by admin %s", payment_id, admin_telegram_id)
