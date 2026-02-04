from sqlalchemy import select

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models.buyer import Buyer


class BuyerGateway(Gateway):
    async def create_buyer(self, buyer: Buyer) -> None:
        self._session.add(buyer)
        await self._session.flush()

    async def get_buyer_by_id(self, buyer_id: int) -> Buyer | None:
        return await self._session.scalar(select(Buyer).where(Buyer.id == buyer_id))

    async def get_buyer_by_telegram_id_and_nm_id(self, telegram_id: int, nm_id: int) -> Buyer | None:
        return await self._session.scalar(select(Buyer).where(Buyer.telegram_id == telegram_id, Buyer.nm_id == nm_id))

    async def get_buyers_by_cabinet_id(self, cabinet_id: int) -> list[Buyer]:
        result = await self._session.scalars(
            select(Buyer).where(Buyer.cabinet_id == cabinet_id).order_by(Buyer.created_at.desc())
        )
        return list(result)
