import pytest

from axiomai.config import SuperbankingConfig
from axiomai.infrastructure.superbanking import Superbanking


def _make_config() -> SuperbankingConfig:
    return SuperbankingConfig(
        **{
            "SUPERBANKING_API_KEY": "test-api-key",
            "SUPERBANKING_CABINET_ID": "cabinet-1",
            "SUPERBANKING_PROJECT_ID": "project-1",
            "SUPERBANKING_CLEARING_CENTER_ID": "clearing-1",
        }
    )


def test_create_payment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config())
    captured: dict = {}

    def fake_post_json(*, url: str, payload: dict, log_context: str, add_idempotency_token: bool = True) -> dict:
        captured["url"] = url
        captured["payload"] = payload
        captured["log_context"] = log_context
        captured["add_idempotency_token"] = add_idempotency_token
        return {"data": {"payout": {"id": 123}}}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    order_number = "payment-1"
    cabinet_transaction_id = superbanking.create_payment(
        phone_number="+7 (910) 111-22-33",
        bank_name_rus="Газпромбанк",
        amount=100,
        order_number=order_number,
    )

    assert cabinet_transaction_id == "123"
    assert captured["payload"]["cabinetId"] == "cabinet-1"
    assert captured["payload"]["projectId"] == "project-1"
    assert captured["payload"]["clearingCenterId"] == "clearing-1"
    assert captured["payload"]["orderNumber"] == order_number
    assert captured["payload"]["phone"].startswith("00")
    assert captured["payload"]["amount"] == 100
    assert captured["payload"]["bank"] == superbanking._get_bank_identifier_by_bank_name_rus("Газпромбанк")


def test_create_payment_unknown_bank_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config())

    def fake_post_json(*args, **kwargs) -> dict:  # noqa: ANN001,ANN002,ANN003
        raise AssertionError("Should not call _post_json when bank is unknown")

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    with pytest.raises(ValueError, match="Unknown bank"):
        superbanking.create_payment(
            phone_number="+7 910 111 22 33",
            bank_name_rus="Неизвестный банк",
            amount=100,
            order_number="payment-2",
        )


def test_sign_payment_success(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config())
    captured: dict = {}

    def fake_post_json(*, url: str, payload: dict, log_context: str, add_idempotency_token: bool = True) -> dict:
        captured["payload"] = payload
        return {"result": True}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    assert superbanking.sign_payment("tx-1") is True
    assert captured["payload"]["cabinetId"] == "cabinet-1"
    assert captured["payload"]["cabinetTransactionId"] == "tx-1"


def test_sign_payment_invalid_result_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config())

    def fake_post_json(*, url: str, payload: dict, log_context: str, add_idempotency_token: bool = True) -> dict:
        return {"result": "not-bool"}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    with pytest.raises(ValueError, match="Unexpected Superbanking sign response"):
        superbanking.sign_payment("tx-2")


def test_confirm_operation_success(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config())
    captured: dict = {}

    def fake_post_json(*, url: str, payload: dict, log_context: str, add_idempotency_token: bool = True) -> dict:
        captured["payload"] = payload
        captured["add_idempotency_token"] = add_idempotency_token
        return {"data": {"url": "https://example.com/receipt.pdf"}}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    receipt_url = superbanking.confirm_operation("payment-3")
    assert receipt_url == "https://example.com/receipt.pdf"
    assert captured["payload"]["cabinetId"] == "cabinet-1"
    assert captured["payload"]["orderNumber"] == "payment-3"
    assert captured["add_idempotency_token"] is False


def test_confirm_operation_missing_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    superbanking = Superbanking(_make_config())

    def fake_post_json(*, url: str, payload: dict, log_context: str, add_idempotency_token: bool = True) -> dict:
        return {"data": {}}

    monkeypatch.setattr(superbanking, "_post_json", fake_post_json)

    with pytest.raises(ValueError, match="Unexpected Superbanking confirm response"):
        superbanking.confirm_operation("payment-4")
