from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import Payment


class PaymentGateway(Gateway):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_payment(self, payment: Payment) -> None:
        self._session.add(payment)
        await self._session.flush()

    async def get_payment_by_id(self, payment_id: int) -> Payment | None:
        return await self._session.scalar(select(Payment).where(Payment.id == payment_id))
