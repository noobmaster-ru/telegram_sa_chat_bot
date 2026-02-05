from typing import Callable, Awaitable

from dishka import Scope, provide, provide_all
from sqlalchemy.ext.asyncio import AsyncSession

from axiomai.application.interactors.buy_leads.buy_leads import BuyLeads
from axiomai.application.interactors.buy_leads.cancel_payment import CancelBuyLeadsPayment
from axiomai.application.interactors.buy_leads.confirm_payment import ConfirmBuyLeadsPayment
from axiomai.application.interactors.buy_leads.mark_payment_waiting_confirm import MarkBuyLeadsPaymentWaitingConfirm
from axiomai.application.interactors.create_buyer import CreateBuyer
from axiomai.application.interactors.create_user import CreateSeller
from axiomai.application.interactors.observe_balance_notifications import ObserveBalanceNotifications
from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.application.interactors.sync_cashback_tables import SyncCashbackTables
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.di import GatewaysProvider
from axiomai.infrastructure.message_debouncer import MessageData


class FakeTransactionManager(TransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.flush()

    async def rollback(self) -> None:
        await self._session.rollback()


class FakeMessageDebouncer:
    async def add_message(
        self,
        business_connection_id: str,
        chat_id: int,
        message_data: MessageData,
        process_callback: Callable[[str, int, list[MessageData]], Awaitable[None]],
    ) -> None:
        await process_callback(business_connection_id, chat_id, [message_data])


class MocksProvider(GatewaysProvider):
    scope = Scope.APP

    transaction_manager = provide(FakeTransactionManager, provides=TransactionManager)

    interactors = provide_all(
        CreateSeller,
        ObserveBalanceNotifications,
        ObserveCashbackTables,
        SyncCashbackTables,
        BuyLeads,
        ConfirmBuyLeadsPayment,
        CancelBuyLeadsPayment,
        MarkBuyLeadsPaymentWaitingConfirm,
        CreateBuyer,
    )
