import logging

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.application.exceptions.cashback_table import CashbackTableNotFoundError
from axiomai.application.exceptions.user import UserNotFoundError
from axiomai.constants import PRICE_PER_LEAD
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.models import Payment
from axiomai.infrastructure.database.models.payment import PaymentMethod, PaymentStatus, PaymentType, ServiceType
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class BuyLeads:
    def __init__(
        self,
        tm: TransactionManager,
        user_gateway: UserGateway,
        cabinet_gateway: CabinetGateway,
        cashback_table_gateway: CashbackTableGateway,
        payment_gateway: PaymentGateway,
    ) -> None:
        self._tm = tm
        self._user_gateway = user_gateway
        self._cabinet_gateway = cabinet_gateway
        self._cashback_table_gateway = cashback_table_gateway
        self._payment_gateway = payment_gateway

    async def execute(self, telegram_id: int, leads_amount: int) -> int:
        user = await self._user_gateway.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFoundError(f"User with telegram_id {telegram_id} not found")

        cabinet = await self._cabinet_gateway.get_cabinet_by_telegram_id(telegram_id)
        if not cabinet:
            raise CabinetNotFoundError(f"Cabinet for user {telegram_id} not found")

        cashback_table = await self._cashback_table_gateway.get_active_cashback_table_by_telegram_id(telegram_id)
        if not cashback_table:
            raise CashbackTableNotFoundError(f"No active cashback table found for the user {telegram_id}")

        amount = leads_amount * PRICE_PER_LEAD

        payment = Payment(
            user_id=user.id,
            email=user.email,
            cashback_table_id=cashback_table.id if cashback_table else None,
            amount=amount,
            status=PaymentStatus.CREATED,
            payment_method=PaymentMethod.KIRILL_CARD,
            payment_type=PaymentType.REGULAR,
            service_type=ServiceType.CASHBACK,
            service_data={
                "service": "cashback",
                "service_id": cashback_table.id if cashback_table else None,
                "months": None,
                "leads": leads_amount,
                "discounts": [{"discount": None, "description": None, "fix_price": None}],
                "price_per_lead": PRICE_PER_LEAD,
            },
        )

        await self._payment_gateway.create_payment(payment)
        await self._tm.commit()

        logger.info("created payment %s for user %s to buy %s leads", payment.id, telegram_id, leads_amount)

        return payment.id
