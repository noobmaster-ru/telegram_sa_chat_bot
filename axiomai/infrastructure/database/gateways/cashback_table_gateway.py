import datetime

from sqlalchemy import select

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import Cabinet, User
from axiomai.infrastructure.database.models.cashback_table import CashbackTable, CashbackTableStatus


class CashbackTableGateway(Gateway):
    async def create_cashback_table(self, cashback_table: CashbackTable) -> None:
        self._session.add(cashback_table)
        await self._session.flush()

    async def get_new_cashback_tables(self) -> list[CashbackTable]:
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
        cashback_tables = await self._session.scalars(
            select(CashbackTable).where(
                CashbackTable.status.in_([CashbackTableStatus.NEW, CashbackTableStatus.WAITING_WRITE_PERMISSION]),
                CashbackTable.created_at >= since,
            )
        )
        return list(cashback_tables)

    async def get_cashback_table_by_table_id(self, table_id: str) -> None:
        return await self._session.scalar(select(CashbackTable).where(CashbackTable.table_id == table_id))

    async def get_cashback_table_by_id(self, cashback_table_id: int) -> CashbackTable | None:
        return await self._session.scalar(select(CashbackTable).where(CashbackTable.id == cashback_table_id))

    async def get_active_cashback_table_by_telegram_id(self, telegram_id: int) -> CashbackTable | None:
        return await self._session.scalar(
            select(CashbackTable)
            .join(Cabinet)
            .join(User)
            .where(
                User.telegram_id == telegram_id,
                CashbackTable.status.in_([CashbackTableStatus.VERIFIED, CashbackTableStatus.PAID]),
            )
        )

    async def get_active_cashback_table_by_business_connection_id(
        self, business_connection_id: str
    ) -> CashbackTable | None:
        return await self._session.scalar(
            select(CashbackTable)
            .join(Cabinet)
            .where(
                Cabinet.business_connection_id == business_connection_id,
                CashbackTable.status.in_([CashbackTableStatus.VERIFIED, CashbackTableStatus.PAID]),
            )
        )
