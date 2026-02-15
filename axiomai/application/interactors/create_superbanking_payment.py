import contextlib
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
        buyer_id: int,
        phone_number: str | None,
        bank: str | None,
        amount: str | int | None,
    ) -> str | None:
        buyer = await self._buyer_gateway.get_buyer_by_id(buyer_id)
        if not buyer:
            raise ValueError(f"Buyer with id {buyer_id} not found")

        if phone_number:
            buyer.phone_number = phone_number
        if bank:
            buyer.bank = bank
        if amount:
            with contextlib.suppress(ValueError, TypeError):
                if not buyer.amount:
                    buyer.amount = int(amount)

        if not (buyer.phone_number and buyer.bank and buyer.amount):
            await self._transaction_manager.commit()
            return None

        order_number = self._superbanking_payout_gateway.build_order_number(
            buyer_id=buyer.id,
            nm_id=buyer.nm_id,
            phone_number=buyer.phone_number,
            bank=buyer.bank,
            amount=buyer.amount,
        )
        payout = await self._superbanking_payout_gateway.create_payout(
            buyer_id=buyer.id,
            nm_id=buyer.nm_id,
            phone_number=buyer.phone_number,
            bank=buyer.bank,
            amount=buyer.amount,
            order_number=order_number,
        )
        await self._transaction_manager.commit()

        try:
            cabinet_transaction_id = self._superbanking.create_payment(
                phone_number=buyer.phone_number,
                bank_name_rus=buyer.bank,
                amount=buyer.amount,
                order_number=payout.order_number,
            )
        except Exception as exc:
            logger.exception("Failed to create_payment() Superbanking payout for buyer_id=%s", buyer_id)
            raise CreatePaymentError from exc

        try:
            self._ensure_payment_signed(
                cabinet_transaction_id=cabinet_transaction_id,
                order_number=payout.order_number,
                buyer_id=buyer_id,
            )
        except SignPaymentError:
            raise
        except Exception as exc:
            logger.exception("Failed to sign_payment() Superbanking payout for buyer_id=%s", buyer_id)
            raise SignPaymentError from exc

        return payout.order_number

    def _ensure_payment_signed(self, *, cabinet_transaction_id: str, order_number: str, buyer_id: int) -> None:
        is_succeed_payment = self._superbanking.sign_payment(
            cabinet_transaction_id=cabinet_transaction_id,
            order_number=order_number,
        )
        if not is_succeed_payment:
            logger.error("Superbanking sign_payment() returned False for buyer_id=%s", buyer_id)
            raise SignPaymentError("Superbanking sign_payment() returned False")
