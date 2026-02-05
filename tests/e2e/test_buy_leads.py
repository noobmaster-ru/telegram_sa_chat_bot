import pytest
from sqlalchemy import select

from axiomai.application.interactors.buy_leads.buy_leads import BuyLeads
from axiomai.application.interactors.buy_leads.cancel_payment import CancelBuyLeadsPayment
from axiomai.application.interactors.buy_leads.confirm_payment import ConfirmBuyLeadsPayment
from axiomai.application.interactors.buy_leads.mark_payment_waiting_confirm import MarkBuyLeadsPaymentWaitingConfirm
from axiomai.application.exceptions.payment import (
    PaymentAlreadyProcessedError,
)
from axiomai.constants import PRICE_PER_LEAD
from axiomai.infrastructure.database.models import Payment
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.database.models.payment import PaymentStatus


@pytest.fixture
async def buy_leads(di_container) -> BuyLeads:
    return await di_container.get(BuyLeads)


@pytest.fixture
async def confirm_payment(di_container) -> ConfirmBuyLeadsPayment:
    return await di_container.get(ConfirmBuyLeadsPayment)


@pytest.fixture
async def cancel_payment(di_container) -> CancelBuyLeadsPayment:
    return await di_container.get(CancelBuyLeadsPayment)


@pytest.fixture
async def mark_payment_waiting(di_container) -> MarkBuyLeadsPaymentWaitingConfirm:
    return await di_container.get(MarkBuyLeadsPaymentWaitingConfirm)


async def test_buy_leads_creates_payment(buy_leads, session, user_factory, cabinet_factory, cashback_table_factory):
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.VERIFIED)

    leads_amount = 100
    await buy_leads.execute(telegram_id=user.telegram_id, leads_amount=leads_amount)

    payment = await session.scalar(select(Payment).where(Payment.user_id == user.id))
    assert payment is not None
    assert payment.status == PaymentStatus.CREATED
    assert payment.amount == leads_amount * PRICE_PER_LEAD
    assert payment.service_data["leads"] == leads_amount


async def test_confirm_payment_adds_leads_balance(
    buy_leads, confirm_payment, mark_payment_waiting, session, user_factory, cabinet_factory, cashback_table_factory
):
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id, leads_balance=0)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.VERIFIED)

    leads_amount = 50
    await buy_leads.execute(telegram_id=user.telegram_id, leads_amount=leads_amount)

    payment = await session.scalar(select(Payment).where(Payment.user_id == user.id))
    await mark_payment_waiting.execute(payment_id=payment.id)
    await confirm_payment.execute(admin_telegram_id=694144143, payment_id=payment.id)

    assert payment.status == PaymentStatus.SUCCEEDED
    assert cabinet.leads_balance == leads_amount


async def test_cancel_payment_sets_canceled_status(
    buy_leads, cancel_payment, mark_payment_waiting, session, user_factory, cabinet_factory, cashback_table_factory
):
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.VERIFIED)

    await buy_leads.execute(telegram_id=user.telegram_id, leads_amount=100)

    payment = await session.scalar(select(Payment).where(Payment.user_id == user.id))
    await mark_payment_waiting.execute(payment_id=payment.id)
    await cancel_payment.execute(admin_telegram_id=694144143, payment_id=payment.id, reason="Test cancel")

    await session.refresh(payment)

    assert payment.status == PaymentStatus.CANCELED
    assert payment.canceled_reason == "Test cancel"


async def test_mark_payment_waiting_confirm(
    buy_leads, mark_payment_waiting, session, user_factory, cabinet_factory, cashback_table_factory
):
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.VERIFIED)

    await buy_leads.execute(telegram_id=user.telegram_id, leads_amount=100)

    payment = await session.scalar(select(Payment).where(Payment.user_id == user.id))
    assert payment.status == PaymentStatus.CREATED

    await mark_payment_waiting.execute(payment_id=payment.id)

    assert payment.status == PaymentStatus.WAITING_CONFIRM


async def test_confirm_already_processed_payment_raises_error(
    buy_leads, confirm_payment, mark_payment_waiting, session, user_factory, cabinet_factory, cashback_table_factory
):
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.VERIFIED)

    await buy_leads.execute(telegram_id=user.telegram_id, leads_amount=100)

    payment = await session.scalar(select(Payment).where(Payment.user_id == user.id))
    await mark_payment_waiting.execute(payment_id=payment.id)
    await confirm_payment.execute(admin_telegram_id=694144143, payment_id=payment.id)

    with pytest.raises(PaymentAlreadyProcessedError):
        await confirm_payment.execute(admin_telegram_id=694144143, payment_id=payment.id)
