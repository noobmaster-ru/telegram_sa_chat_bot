import logging

from axiomai.application.exceptions.superbanking import CreatePaymentError, SignPaymentError
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.superbanking_payout import SuperbankingPayoutGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.superbanking import Superbanking

logger = logging.getLogger(__name__)


class CreateSuperbankingPayment:
    def __init__(
        self,
        buyer_gateway: BuyerGateway,
        superbanking_payout_gateway: SuperbankingPayoutGateway,
        transaction_manager: TransactionManager,
        superbanking: Superbanking,
    ) -> None:
        self._buyer_gateway = buyer_gateway
        self._superbanking_payout_gateway = superbanking_payout_gateway
        self._transaction_manager = transaction_manager
        self._superbanking = superbanking

    async def execute(
        self,
        *,
        telegram_id: int,
        cabinet_id: int,
        phone_number: str,
        bank: str,
    ) -> str:
        buyers = await self._buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(telegram_id, cabinet_id)

        nm_ids = []
        total_amount = 0
        for buyer in buyers:
            buyer.phone_number = phone_number
            buyer.bank = bank

            nm_ids.append(buyer.nm_id)
            total_amount += buyer.amount

        order_number = self._superbanking_payout_gateway.build_order_number(
            telegram_id=telegram_id,
            nm_ids=nm_ids,
            phone_number=phone_number,
            bank=bank,
            amount=total_amount,
        )
        payout = await self._superbanking_payout_gateway.create_payout(
            telegram_id=telegram_id,
            nm_ids=nm_ids,
            phone_number=phone_number,
            bank=bank,
            amount=total_amount,
            order_number=order_number,
        )

        await self._transaction_manager.commit()

        try:
            cabinet_transaction_id = self._superbanking.create_payment(
                phone_number=phone_number,
                bank_name_rus=bank,
                amount=total_amount,
                order_number=payout.order_number,
            )
        except CreatePaymentError:
            logger.exception("Failed to create_payment() Superbanking payout for payout_id=%s", payout.id)
            raise

        try:
            self._superbanking.sign_payment(cabinet_transaction_id=cabinet_transaction_id)
        except SignPaymentError:
            logger.exception("Failed to sign_payment() Superbanking payout for payout_id=%s", payout.id)
            raise

        return payout.order_number

