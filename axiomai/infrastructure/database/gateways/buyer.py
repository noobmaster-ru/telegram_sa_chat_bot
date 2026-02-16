from datetime import datetime

from sqlalchemy import select, and_

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

    async def get_inactive_buyers(self, inactive_since: datetime) -> list[Buyer]:
        result = await self._session.scalars(
            select(Buyer).where(
                Buyer.is_superbanking_paid.is_(False),
                Buyer.is_paid_manually.is_(False),
                Buyer.updated_at < inactive_since,
                Buyer.chat_history != [],
            )
        )
        return list(result)

    async def get_active_buyers_by_telegram_id_and_cabinet_id(
        self, telegram_id: int, cabinet_id: int
    ) -> list[Buyer]:
        result = await self._session.scalars(
            select(Buyer).where(
                Buyer.telegram_id == telegram_id,
                Buyer.cabinet_id == cabinet_id,
                Buyer.is_superbanking_paid.is_(False),
                Buyer.is_paid_manually.is_(False),
            ).order_by(Buyer.created_at.desc())
        )
        return list(result)

    async def get_incompleted_buyers_by_telegram_id_and_cabinet_id(
        self, telegram_id: int, cabinet_id: int
    ) -> list[Buyer]:
        result = await self._session.scalars(
            select(Buyer).where(
                Buyer.telegram_id == telegram_id,
                Buyer.cabinet_id == cabinet_id,
                Buyer.is_superbanking_paid.is_(False),
                Buyer.is_paid_manually.is_(False),
                ~and_(Buyer.is_ordered, Buyer.is_left_feedback, Buyer.is_cut_labels),
            ).order_by(Buyer.created_at.desc())
        )

        return list(result)