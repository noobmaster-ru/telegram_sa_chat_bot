import datetime

from sqlalchemy import select

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import Cabinet, User
from axiomai.infrastructure.database.models.buyer import Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackArticle, CashbackTable, CashbackTableStatus


class CashbackTableGateway(Gateway):
    async def create_cashback_table(self, cashback_table: CashbackTable) -> None:
        self._session.add(cashback_table)
        await self._session.flush()

    async def create_article(self, article: CashbackArticle) -> None:
        self._session.add(article)
        await self._session.flush()

    async def delete_article(self, article: CashbackArticle) -> None:
        await self._session.delete(article)

    async def get_new_cashback_tables(self) -> list[CashbackTable]:
        since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=24)
        cashback_tables = await self._session.scalars(
            select(CashbackTable).where(
                CashbackTable.status.in_([CashbackTableStatus.NEW, CashbackTableStatus.WAITING_WRITE_PERMISSION]),
                CashbackTable.created_at >= since,
            )
        )
        return list(cashback_tables)

    async def get_cashback_table_by_table_id(self, table_id: str) -> CashbackTable | None:
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

    async def get_active_cashback_tables(self) -> list[CashbackTable]:
        cashback_tables = await self._session.scalars(
            select(CashbackTable).where(
                CashbackTable.status.in_([CashbackTableStatus.VERIFIED, CashbackTableStatus.PAID]),
            )
        )
        return list(cashback_tables)

    async def get_articles_by_cabinet_id(self, cabinet_id: int) -> list[CashbackArticle]:
        articles = await self._session.scalars(select(CashbackArticle).where(CashbackArticle.cabinet_id == cabinet_id))
        return list(articles)

    async def get_in_stock_cashback_articles_by_cabinet_id(
        self, cabinet_id: int, telegram_id: int
    ) -> list[CashbackArticle]:
        # True if user already bought smt
        already_bought_something_subq = (
            select(Buyer.id)
            .where(
                Buyer.telegram_id == telegram_id,
                Buyer.nm_id == CashbackArticle.nm_id,
                Buyer.cabinet_id == cabinet_id,
            )
            .exists()
        )
        articles = await self._session.scalars(
            select(CashbackArticle).where(
                CashbackArticle.cabinet_id == cabinet_id,
                CashbackArticle.in_stock.is_(True),
                ~already_bought_something_subq,
            )
        )

        return list(articles)

    async def get_cashback_article_by_id(self, article_id: int) -> CashbackArticle:
        return await self._session.scalar(select(CashbackArticle).where(CashbackArticle.id == article_id))
