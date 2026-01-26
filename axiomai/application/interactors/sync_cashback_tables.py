import datetime
import logging

from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.models.cashback_table import CashbackArticle
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.google_sheets import GoogleSheetsGateway

logger = logging.getLogger(__name__)


class SyncCashbackTables:
    def __init__(
        self,
        cashback_table_gateway: CashbackTableGateway,
        google_sheets_gateway: GoogleSheetsGateway,
        transaction_manager: TransactionManager,
    ) -> None:
        self._cashback_table_gateway = cashback_table_gateway
        self._google_sheets_gateway = google_sheets_gateway
        self._transaction_manager = transaction_manager

    async def execute(self) -> None:
        tables = await self._cashback_table_gateway.get_active_cashback_tables()

        for table in tables:
            try:
                articles_dto = await self._google_sheets_gateway.get_cashback_articles(table.table_id)
            except Exception as e:
                logger.exception("failed to fetch articles from table %s", table.table_id, exc_info=e)
                continue

            existing_articles = await self._cashback_table_gateway.get_articles_by_cabinet_id(table.cabinet_id)
            existing_by_nm_id = {a.nm_id: a for a in existing_articles}
            new_nm_ids = {dto.nm_id for dto in articles_dto}

            # Update existing and create new
            for dto in articles_dto:
                if dto.nm_id in existing_by_nm_id:
                    article = existing_by_nm_id[dto.nm_id]
                    article.title = dto.title
                    article.image_url = dto.image_url
                    article.brand_name = dto.brand_name
                    article.instruction_text = dto.instruction_text
                    article.in_stock = dto.in_stock
                else:
                    new_article = CashbackArticle(
                        cabinet_id=table.cabinet_id,
                        nm_id=dto.nm_id,
                        title=dto.title,
                        image_url=dto.image_url,
                        brand_name=dto.brand_name,
                        instruction_text=dto.instruction_text,
                        in_stock=dto.in_stock,
                    )
                    await self._cashback_table_gateway.create_article(new_article)

            # Delete removed
            for nm_id, article in existing_by_nm_id.items():
                if nm_id not in new_nm_ids:
                    await self._cashback_table_gateway.delete_article(article)

            table.last_synced_at = datetime.datetime.now(datetime.UTC)
            await self._transaction_manager.commit()
