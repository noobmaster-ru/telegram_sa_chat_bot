import pytest

from axiomai.application.exceptions.superbanking import CreatePaymentError, SignPaymentError
from axiomai.application.interactors.create_superbanking_payment import CreateSuperbankingPayment


class FakeBuyer:
    def __init__(
        self,
        *,
        buyer_id: int = 1,
        nm_id: int = 10,
        phone_number: str | None = None,
        bank: str | None = None,
        amount: int | None = None,
    ) -> None:
        self.id = buyer_id
        self.nm_id = nm_id
        self.phone_number = phone_number
        self.bank = bank
        self.amount = amount


class FakeBuyerGateway:
    def __init__(self, buyer: FakeBuyer | None) -> None:
        self._buyer = buyer

    async def get_buyer_by_id(self, buyer_id: int) -> FakeBuyer | None:
        return self._buyer


class FakePayout:
    def __init__(self, order_number: str) -> None:
        self.order_number = order_number


class FakeSuperbankingPayoutGateway:
    def __init__(self) -> None:
        self.created: dict | None = None

    def build_order_number(
        self,
        *,
        buyer_id: int,
        nm_id: int,
        phone_number: str,
        bank: str,
        amount: int,
    ) -> str:
        return "payment-abc123"

    async def create_payout(self, **kwargs):  # noqa: ANN003
        self.created = kwargs
        return FakePayout(order_number=kwargs["order_number"])


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeSuperbanking:
    def __init__(self, *, sign_ok: bool = True, create_raises: bool = False) -> None:
        self.sign_ok = sign_ok
        self.create_raises = create_raises
        self.created: dict | None = None
        self.signed: list[str] = []

    def create_payment(self, **kwargs):  # noqa: ANN003
        if self.create_raises:
            raise RuntimeError("boom")
        self.created = kwargs
        return "tx-1"

    def sign_payment(self, cabinet_transaction_id: str) -> bool:
        self.signed.append(cabinet_transaction_id)
        return self.sign_ok


@pytest.mark.asyncio
async def test_execute_missing_buyer_raises() -> None:
    interactor = CreateSuperbankingPayment(
        buyer_gateway=FakeBuyerGateway(None),
        superbanking_payout_gateway=FakeSuperbankingPayoutGateway(),
        transaction_manager=FakeTransactionManager(),
        superbanking=FakeSuperbanking(),
    )

    with pytest.raises(ValueError, match="Buyer with id 1 not found"):
        await interactor.execute(buyer_id=1, phone_number=None, bank=None, amount=None)


@pytest.mark.asyncio
async def test_execute_without_required_fields_commits_and_returns_none() -> None:
    buyer = FakeBuyer(phone_number=None, bank=None, amount=None)
    tm = FakeTransactionManager()
    superbanking = FakeSuperbanking()
    interactor = CreateSuperbankingPayment(
        buyer_gateway=FakeBuyerGateway(buyer),
        superbanking_payout_gateway=FakeSuperbankingPayoutGateway(),
        transaction_manager=tm,
        superbanking=superbanking,
    )

    result = await interactor.execute(buyer_id=1, phone_number=None, bank=None, amount=None)

    assert result is None
    assert tm.commits == 1
    assert superbanking.created is None


@pytest.mark.asyncio
async def test_execute_happy_path_returns_order_number() -> None:
    buyer = FakeBuyer(phone_number="123", bank="Bank", amount=100)
    payout_gateway = FakeSuperbankingPayoutGateway()
    superbanking = FakeSuperbanking(sign_ok=True)
    interactor = CreateSuperbankingPayment(
        buyer_gateway=FakeBuyerGateway(buyer),
        superbanking_payout_gateway=payout_gateway,
        transaction_manager=FakeTransactionManager(),
        superbanking=superbanking,
    )

    result = await interactor.execute(buyer_id=1, phone_number=None, bank=None, amount=None)

    assert result == "payment-abc123"
    assert superbanking.created is not None
    assert superbanking.created["order_number"] == "payment-abc123"
    assert superbanking.signed == ["tx-1"]


@pytest.mark.asyncio
async def test_execute_create_payment_error() -> None:
    buyer = FakeBuyer(phone_number="123", bank="Bank", amount=100)
    interactor = CreateSuperbankingPayment(
        buyer_gateway=FakeBuyerGateway(buyer),
        superbanking_payout_gateway=FakeSuperbankingPayoutGateway(),
        transaction_manager=FakeTransactionManager(),
        superbanking=FakeSuperbanking(create_raises=True),
    )

    with pytest.raises(CreatePaymentError):
        await interactor.execute(buyer_id=1, phone_number=None, bank=None, amount=None)


@pytest.mark.asyncio
async def test_execute_sign_payment_error() -> None:
    buyer = FakeBuyer(phone_number="123", bank="Bank", amount=100)
    interactor = CreateSuperbankingPayment(
        buyer_gateway=FakeBuyerGateway(buyer),
        superbanking_payout_gateway=FakeSuperbankingPayoutGateway(),
        transaction_manager=FakeTransactionManager(),
        superbanking=FakeSuperbanking(sign_ok=False),
    )

    with pytest.raises(SignPaymentError):
        await interactor.execute(buyer_id=1, phone_number=None, bank=None, amount=None)
