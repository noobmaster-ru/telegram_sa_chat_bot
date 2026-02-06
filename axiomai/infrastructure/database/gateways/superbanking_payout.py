from sqlalchemy.ext.asyncio import AsyncSession

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import SuperbankingPayout


class SuperbankingPayoutGateway(Gateway):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_payout(
        self,
        *,
        buyer_id: int,
        nm_id: int,
        phone_number: str,
        bank: str,
        amount: int,
    ) -> SuperbankingPayout:
        payout = SuperbankingPayout(
            buyer_id=buyer_id,
            nm_id=nm_id,
            phone_number=phone_number,
            bank=bank,
            amount=amount,
        )
        self._session.add(payout)
        await self._session.flush()
        return payout
