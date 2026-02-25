from unittest.mock import MagicMock, AsyncMock

import pytest
from sqlalchemy import select

from axiomai.application.exceptions.payment import NotEnoughBalanceError
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
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    order_number = await create_superbanking_payment.execute(
        telegram_id=buyer.telegram_id,
        cabinet_id=buyer.cabinet_id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=200,
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
    superbanking.create_payment = AsyncMock(side_effect=CreatePaymentError("Unknown bank"))
    superbanking.sign_payment = AsyncMock(return_value=True)

    with pytest.raises(CreatePaymentError):
        await create_superbanking_payment.execute(
            telegram_id=buyer.telegram_id,
            cabinet_id=buyer.cabinet_id,
            phone_number="+7 910 111 22 33",
            bank="Неизвестный банк",
            amount=200,
        )

    assert buyer.is_superbanking_paid is False
    assert cabinet.balance == 1000


async def test_create_superbanking_payment_distributes_amount_to_buyers_without_amount(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(balance=1000, is_superbanking_connect=True)
    buyer1 = Buyer(
        cabinet_id=cabinet.id,
        username="user1",
        fullname="User 1",
        telegram_id=123456,
        nm_id=111,
        amount=None,
    )
    buyer2 = Buyer(
        cabinet_id=cabinet.id,
        username="user2",
        fullname="User 2",
        telegram_id=123456,
        nm_id=222,
        amount=None,
    )
    session.add_all([buyer1, buyer2])
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=123456,
        cabinet_id=cabinet.id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=400,
    )

    assert buyer1.amount == 200
    assert buyer2.amount == 200
    assert buyer1.is_superbanking_paid is True
    assert buyer2.is_superbanking_paid is True


async def test_create_superbanking_payment_does_not_override_existing_amounts(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(balance=1000, is_superbanking_connect=True)
    buyer1 = Buyer(
        cabinet_id=cabinet.id,
        username="user1",
        fullname="User 1",
        telegram_id=123456,
        nm_id=111,
        amount=100,
    )
    buyer2 = Buyer(
        cabinet_id=cabinet.id,
        username="user2",
        fullname="User 2",
        telegram_id=123456,
        nm_id=222,
        amount=300,
    )
    session.add_all([buyer1, buyer2])
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=123456,
        cabinet_id=cabinet.id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=999,
    )

    assert buyer1.amount == 100
    assert buyer2.amount == 300


async def test_create_superbanking_payment_mixed_buyers_with_and_without_amount(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    cabinet = await cabinet_factory(balance=1000, is_superbanking_connect=True)
    buyer_with_amount = Buyer(
        cabinet_id=cabinet.id,
        username="user1",
        fullname="User 1",
        telegram_id=123456,
        nm_id=111,
        amount=150,
    )
    buyer_without_amount = Buyer(
        cabinet_id=cabinet.id,
        username="user2",
        fullname="User 2",
        telegram_id=123456,
        nm_id=222,
        amount=None,
    )
    session.add_all([buyer_with_amount, buyer_without_amount])
    await session.flush()

    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-1")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=123456,
        cabinet_id=cabinet.id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=400,
    )

    assert buyer_with_amount.amount == 150
    assert buyer_without_amount.amount == 200


async def test_create_superbanking_payment_raises_not_enough_balance(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    total_amount = 200
    total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
    buyer, cabinet = await _create_buyer(
        session, cabinet_factory, amount=total_amount, cabinet_balance=total_charge - 1
    )
    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock()
    superbanking.sign_payment = AsyncMock()

    with pytest.raises(NotEnoughBalanceError):
        await create_superbanking_payment.execute(
            telegram_id=buyer.telegram_id,
            cabinet_id=buyer.cabinet_id,
            phone_number="+7 910 111 22 33",
            bank="Тинькофф",
            amount=total_amount,
        )

    superbanking.create_payment.assert_not_called()
    assert cabinet.balance == total_charge - 1


async def test_create_superbanking_payment_succeeds_with_exact_balance(
    create_superbanking_payment, di_container, session, cabinet_factory
):
    total_amount = 200
    total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
    buyer, cabinet = await _create_buyer(
        session, cabinet_factory, amount=total_amount, cabinet_balance=total_charge
    )
    superbanking = await di_container.get(Superbanking)
    superbanking.create_payment = AsyncMock(return_value="tx-exact")
    superbanking.sign_payment = AsyncMock(return_value=True)

    await create_superbanking_payment.execute(
        telegram_id=buyer.telegram_id,
        cabinet_id=buyer.cabinet_id,
        phone_number="+7 910 111 22 33",
        bank="Тинькофф",
        amount=total_amount,
    )

    assert cabinet.balance == 0
