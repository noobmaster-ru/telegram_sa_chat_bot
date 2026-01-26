from sqlalchemy import or_, select

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import CashbackTable, User
from axiomai.infrastructure.database.models.cabinet import Cabinet


class CabinetGateway(Gateway):
    async def create_cabinet(self, cabinet: Cabinet) -> None:
        self._session.add(cabinet)
        await self._session.flush()

    async def get_cabinet_by_telegram_id(self, telegram_id: int) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).join(User).where(User.telegram_id == telegram_id))

    async def get_cabinet_by_link_code(self, link_code: str) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).where(Cabinet.link_code == link_code))

    async def get_cabinet_by_id(self, cabinet_id: int) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).where(Cabinet.id == cabinet_id))

    async def get_cabinet_by_business_account_id(self, business_account_id: int) -> Cabinet | None:
        return await self._session.scalar(select(Cabinet).where(Cabinet.business_account_id == business_account_id))

    async def get_cabinet_by_telegram_id_or_business_account_id(self, telegram_id: int) -> Cabinet | None:
        return await self._session.scalar(
            select(Cabinet)
            .join(User)
            .where(or_(Cabinet.business_account_id == telegram_id, User.telegram_id == telegram_id))
        )

    async def get_cabinet_by_cashback_table_id(self, cashback_table_id: int) -> Cabinet | None:
        return await self._session.scalar(
            select(Cabinet).join(CashbackTable).where(CashbackTable.id == cashback_table_id)
        )
