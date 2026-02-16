from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from axiomai.application.exceptions.superbanking import CreatePaymentError
from axiomai.application.interactors.create_superbanking_payment import CreateSuperbankingPayment
from axiomai.constants import AXIOMAI_COMMISSION, SUPERBANKING_COMMISSION
from axiomai.infrastructure.database.models import Buyer, Cabinet
from axiomai.infrastructure.database.models.superbanking import SuperbankingPayout
from axiomai.infrastructure.superbanking import Superbanking


@pytest.fixture
async def create_superbanking_payment(di_container) -> CreateSuperbankingPayment:
    return await di_container.get(CreateSuperbankingPayment)


async def _create_buyer(
    session,
    cabinet_factory,
    *,
    phone_number=None,
    bank=None,
    amount=None,
    cabinet_balance: int = 0,
) -> tuple[Buyer, Cabinet]:
    cabinet = await cabinet_factory(balance=cabinet_balance, is_superbanking_connect=True)
    buyer = Buyer(
        cabinet_id=cabinet.id,
        username="test_user",
        fullname="Test User",
        telegram_id=123456,
        nm_id=777,
        phone_number=phone_number,
        bank=bank,
        amount=amount,
    )
    session.add(buyer)
    await session.flush()
    return buyer, cabinet


async def test_create_superbanking_payment_creates_payout(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    buyer, cabinet = await _create_buyer(session, cabinet_factory, amount=200, cabinet_balance=1000)
    superbanking = await di_container.get(Superbanking)

    # Override Superbanking mock with sync methods
    superbanking.create_payment = MagicMock(return_value="tx-1")
    superbanking.sign_payment = MagicMock(return_value=True)

    order_number = await create_superbanking_payment.execute(
        telegram_id=buyer.telegram_id,
        cabinet_id=buyer.cabinet_id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
    )

    payout = await session.scalar(select(SuperbankingPayout).where(SuperbankingPayout.order_number == order_number))
    assert payout is not None
    assert payout.order_number == order_number
    assert buyer.is_superbanking_paid is True
    assert cabinet.balance == 1000 - (buyer.amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION)


async def test_create_superbanking_payment_missing_bank_raises(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    buyer, cabinet = await _create_buyer(session, cabinet_factory, amount=200, cabinet_balance=1000)
    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = MagicMock(side_effect=CreatePaymentError("Unknown bank"))
    superbanking.sign_payment = MagicMock(return_value=True)

    with pytest.raises(CreatePaymentError):
        await create_superbanking_payment.execute(
            telegram_id=buyer.telegram_id,
            cabinet_id=buyer.cabinet_id,
            phone_number="+7 910 111 22 33",
            bank="Неизвестный банк",
        )

    assert buyer.is_superbanking_paid is False
    assert cabinet.balance == 1000
