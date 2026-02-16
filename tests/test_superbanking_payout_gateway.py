from axiomai.constants import SUPERBANKING_ORDER_PREFIX
from axiomai.infrastructure.database.gateways.superbanking_payout import SuperbankingPayoutGateway


def test_build_order_number_is_deterministic_and_within_limit() -> None:
    order_number_1 = SuperbankingPayoutGateway.build_order_number(
        telegram_id=1,
        nm_ids=[34542],
        phone_number="+7 (910) 111-22-33",
        bank="Сбер",
        amount=200,
    )
    order_number_2 = SuperbankingPayoutGateway.build_order_number(
        telegram_id=1,
        nm_ids=[34542],
        phone_number="+7 (910) 111-22-33",
        bank="Сбер",
        amount=200,
    )

    assert order_number_1 == order_number_2
    assert order_number_1.startswith(SUPERBANKING_ORDER_PREFIX)
    assert len(order_number_1) <= 30
