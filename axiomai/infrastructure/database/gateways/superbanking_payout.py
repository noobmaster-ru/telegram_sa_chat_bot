import hashlib

from sqlalchemy import select

from axiomai.constants import SUPERBANKING_ORDER_PREFIX
from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import SuperbankingPayout


class SuperbankingPayoutGateway(Gateway):
    @staticmethod
    def build_order_number(
        *,
        telegram_id: int,
        nm_ids: list[int],
        phone_number: str,
        bank: str,
        amount: int,
    ) -> str:
        normalized_bank = bank.strip().lower()
        normalized_phone = "".join(ch for ch in phone_number if ch.isdigit())
        raw_key = f"{telegram_id}:{",".join(map(str, nm_ids))}:{amount}:{normalized_phone}:{normalized_bank}"

        # orderNumber max length is 30 chars (Superbanking API limit)
        max_digest_len = 30 - len(SUPERBANKING_ORDER_PREFIX)
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:max_digest_len]
        return f"{SUPERBANKING_ORDER_PREFIX}{digest}"

    async def create_payout(
        self,
        *,
        telegram_id: int,
        nm_ids: list[int],
        phone_number: str,
        bank: str,
        amount: int,
        order_number: str,
    ) -> SuperbankingPayout:
        existing = await self._session.scalar(
            select(SuperbankingPayout).where(SuperbankingPayout.order_number == order_number)
        )
        if existing:
            return existing

        payout = SuperbankingPayout(
            telegram_id=telegram_id,
            nm_ids=nm_ids,
            order_number=order_number,
            phone_number=phone_number,
            bank=bank,
            amount=amount,
        )
        self._session.add(payout)
        await self._session.flush()
        return payout
