from decimal import Decimal

from sqlalchemy import select

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models.balance_notification import BalanceNotification


class BalanceNotificationGateway(Gateway):
    async def create_notification(
        self, cabinet_id: int, initial_balance: int, threshold: Decimal
    ) -> BalanceNotification:
        notification = BalanceNotification(
            cabinet_id=cabinet_id,
            initial_balance=initial_balance,
            threshold=threshold,
        )
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def get_sent_thresholds(self, cabinet_id: int, initial_balance: int) -> list[Decimal]:
        result = await self._session.scalars(
            select(BalanceNotification.threshold).where(
                BalanceNotification.cabinet_id == cabinet_id,
                BalanceNotification.initial_balance == initial_balance,
            )
        )
        return list(result)
