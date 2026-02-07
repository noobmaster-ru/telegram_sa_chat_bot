from collections.abc import AsyncIterable

from dishka import Provider, Scope, provide, provide_all
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from axiomai.application.interactors.buy_leads.buy_leads import BuyLeads
from axiomai.application.interactors.buy_leads.cancel_payment import CancelBuyLeadsPayment
from axiomai.application.interactors.buy_leads.confirm_payment import ConfirmBuyLeadsPayment
from axiomai.application.interactors.buy_leads.mark_payment_waiting_confirm import MarkBuyLeadsPaymentWaitingConfirm
from axiomai.application.interactors.create_buyer import CreateBuyer
from axiomai.application.interactors.create_cabinet import CreateCabinet
from axiomai.application.interactors.create_cashback_table import CreateCashbackTable
from axiomai.application.interactors.create_superbanking_payment import CreateSuperbankingPayment
from axiomai.application.interactors.create_user import CreateSeller
from axiomai.application.interactors.observe_balance_notifications import ObserveBalanceNotifications
from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.application.interactors.refill_balance.cancel_payment import CancelRefillBalancePayment
from axiomai.application.interactors.refill_balance.confirm_payment import ConfirmRefillBalancePayment
from axiomai.application.interactors.refill_balance.mark_payment_waiting_confirm import (
    MarkRefillBalancePaymentWaitingConfirm,
)
from axiomai.application.interactors.refill_balance.refill_balance import RefillBalance
from axiomai.application.interactors.sync_cashback_tables import SyncCashbackTables
from axiomai.config import Config, MessageDebouncerConfig, OpenAIConfig, SuperbankingConfig
from axiomai.infrastructure.database.gateways.balance_notification import BalanceNotificationGateway
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.gateways.superbanking_payout import SuperbankingPayoutGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.google_sheets import GoogleSheetsGateway
from axiomai.infrastructure.message_debouncer import MessageDebouncer
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.superbanking import Superbanking


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_engine(self, config: Config) -> AsyncIterable[AsyncEngine]:
        engine = create_async_engine(
            config.postgres_uri,
            pool_size=15,
            max_overflow=15,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        yield engine
        await engine.dispose()

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self,
        engine: AsyncEngine,
    ) -> AsyncIterable[AsyncSession]:
        async with AsyncSession(engine, autoflush=False, expire_on_commit=False) as session:
            yield session


class ConfigProvider(Provider):
    @provide(scope=Scope.APP)
    def message_debouncer_config(self, config: Config) -> MessageDebouncerConfig:
        return config.message_debouncer

    @provide(scope=Scope.APP)
    def superbankink_config(self, config: Config) -> SuperbankingConfig:
        return config.superbankink_config

    @provide(scope=Scope.APP)
    def openai_config(self, config: Config) -> OpenAIConfig:
        return config.openai_config


class GatewaysProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_tm(self, session: AsyncSession) -> TransactionManager:
        return session  # type: ignore[return-value]

    google_sheets_gateway = provide(GoogleSheetsGateway, scope=Scope.APP)

    gateways = provide_all(
        BalanceNotificationGateway,
        BuyerGateway,
        CabinetGateway,
        CashbackTableGateway,
        PaymentGateway,
        SuperbankingPayoutGateway,
        UserGateway,
    )


class TgbotInteractorsProvider(Provider):
    superbanking = provide(Superbanking, scope=Scope.APP)
    openai_gateway = provide(OpenAIGateway, scope=Scope.APP)
    message_debouncer = provide(MessageDebouncer, scope=Scope.APP)

    interactors = provide_all(
        CreateSeller,
        CreateCabinet,
        CreateCashbackTable,
        CreateBuyer,
        CreateSuperbankingPayment,
        BuyLeads,
        MarkBuyLeadsPaymentWaitingConfirm,
        ConfirmBuyLeadsPayment,
        CancelBuyLeadsPayment,
        RefillBalance,
        MarkRefillBalancePaymentWaitingConfirm,
        ConfirmRefillBalancePayment,
        CancelRefillBalancePayment,
        scope=Scope.REQUEST,
    )


class ObserverInteractorsProvider(Provider):
    interactors = provide_all(
        ObserveBalanceNotifications,
        ObserveCashbackTables,
        SyncCashbackTables,
        scope=Scope.REQUEST,
    )
