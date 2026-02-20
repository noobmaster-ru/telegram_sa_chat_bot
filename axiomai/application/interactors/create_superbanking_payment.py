import logging

from axiomai.application.exceptions.superbanking import CreatePaymentError, SignPaymentError, SkipSuperbankingError
from axiomai.constants import AXIOMAI_COMMISSION, SUPERBANKING_COMMISSION
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.superbanking_payout import SuperbankingPayoutGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.superbanking import Superbanking

logger = logging.getLogger(__name__)


class CreateSuperbankingPayment:
    def __init__(
        self,
        buyer_gateway: BuyerGateway,
        cabinet_gateway: CabinetGateway,
        superbanking_payout_gateway: SuperbankingPayoutGateway,
        transaction_manager: TransactionManager,
        superbanking: Superbanking,
    ) -> None:
        self._buyer_gateway = buyer_gateway
        self._cabinet_gateway = cabinet_gateway
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
        amount: int | None
    ) -> str:
        cabinet = await self._cabinet_gateway.get_cabinet_by_id(cabinet_id)
        if not cabinet:
            raise ValueError(f"Cabinet with id {cabinet_id} not found")

        buyers = await self._buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(telegram_id, cabinet_id)

        nm_ids = []
        total_amount = 0

        part_amount = (amount or 0) // len(buyers)

        for buyer in buyers:
            buyer.phone_number = phone_number
            buyer.bank = bank

            if not buyer.amount:
                buyer.amount = part_amount

            nm_ids.append(buyer.nm_id)
            total_amount += buyer.amount

        await self._transaction_manager.commit()

        if not cabinet.is_superbanking_connect:
            logger.info(
                "CreateSuperbankingPayment saved requisites without Superbanking payout: cabinet_id=%s",
                cabinet.id,
            )
            await self._transaction_manager.commit()
            raise SkipSuperbankingError(cabinet_id=cabinet.id, is_superbanking_connect=cabinet.is_superbanking_connect)

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

        try:
            cabinet_transaction_id = await self._superbanking.create_payment(
                phone_number=phone_number,
                bank_name_rus=bank,
                amount=total_amount,
                order_number=payout.order_number,
            )
        except CreatePaymentError:
            logger.exception("Failed to create_payment() Superbanking payout for payout_id=%s", payout.id)
            raise

        try:
            await self._superbanking.sign_payment(cabinet_transaction_id=cabinet_transaction_id, order_number=payout.order_number)
        except SignPaymentError:
            logger.exception("Failed to sign_payment() Superbanking payout for payout_id=%s", payout.id)
            raise

        # успешно выплатили юзеру деньги через superbanking_api - списываем деньги с баланса селлера и ставим buyer.is_superbanking_paid = True
        for buyer in buyers:
            buyer.is_superbanking_paid = True
            buyer.is_paid_manually = True

        total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
        cabinet.balance -= total_charge

        await self._transaction_manager.commit()

        return payout.order_number



