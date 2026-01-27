import logging

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.models.buyer import Buyer
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class CreateBuyer:
    def __init__(
        self,
        buyer_gateway: BuyerGateway,
        cashback_table_gateway: CashbackTableGateway,
        transaction_manager: TransactionManager,
    ) -> None:
        self._buyer_gateway = buyer_gateway
        self._cashback_table_gateway = cashback_table_gateway
        self._transaction_manager = transaction_manager

    async def execute(
        self,
        telegram_id: int,
        username: str | None,
        fullname: str,
        article_id: int,
    ) -> Buyer:
        article = await self._cashback_table_gateway.get_cashback_article_by_id(article_id)
        if not article:
            raise ValueError(f"Article with id {article_id} not found")

        existing_buyer = await self._buyer_gateway.get_buyer_by_telegram_id_and_nm_id(
            telegram_id=telegram_id,
            nm_id=article.nm_id,
        )

        if existing_buyer:
            logger.error("buyer already exists for telegram_id %s and nm_id %s", telegram_id, article.nm_id)
            return existing_buyer

        buyer = Buyer(
            cabinet_id=article.cabinet_id,
            telegram_id=telegram_id,
            username=username,
            fullname=fullname,
            nm_id=article.nm_id,
            chat_history=[],
        )

        await self._buyer_gateway.create_buyer(buyer)
        await self._transaction_manager.commit()

        logger.info("buyer created for telegram_id %s, nm_id %s", telegram_id, article.nm_id)

        return buyer
