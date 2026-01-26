from dishka import Scope, provide, provide_all
from sqlalchemy.ext.asyncio import AsyncSession

from axiomai.application.interactors.buy_leads.buy_leads import BuyLeads
from axiomai.application.interactors.buy_leads.cancel_payment import CancelPayment
from axiomai.application.interactors.buy_leads.confirm_payment import ConfirmPayment
from axiomai.application.interactors.buy_leads.mark_payment_waiting_confirm import MarkPaymentWaitingConfirm
from axiomai.application.interactors.create_user import CreateSeller
from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.application.interactors.sync_cashback_tables import SyncCashbackTables
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.di import GatewaysProvider


class FakeTransactionManager(TransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.flush()

    async def rollback(self) -> None:
        await self._session.rollback()


class MocksProvider(GatewaysProvider):
    scope = Scope.APP

    transaction_manager = provide(FakeTransactionManager, provides=TransactionManager)

    interactors = provide_all(
        CreateSeller,
        ObserveCashbackTables,
        SyncCashbackTables,
        BuyLeads,
        ConfirmPayment,
        CancelPayment,
        MarkPaymentWaitingConfirm,
    )
