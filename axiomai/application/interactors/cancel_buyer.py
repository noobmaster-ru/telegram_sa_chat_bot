import logging

from axiomai.application.exceptions.buyer import BuyerAlreadyOrderedError, BuyerNotFoundError
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class CancelBuyer:
    def __init__(self, buyer_gateway: BuyerGateway, tm: TransactionManager) -> None:
        self._buyer_gateway = buyer_gateway
        self._tm = tm

    async def execute(self, buyer_id: int) -> None:
        buyer = await self._buyer_gateway.get_buyer_by_id(buyer_id)
        if not buyer:
            raise BuyerNotFoundError(f"Buyer with id = {buyer_id} not found")

        if buyer.is_ordered:
            raise BuyerAlreadyOrderedError(
                f"Cannot cancel buyer {buyer_id}: order screenshot already accepted"
            )

        buyer.is_canceled = True
        await self._tm.commit()

        logger.info("buyer %s canceled by telegram_id %s", buyer_id, buyer.telegram_id)
