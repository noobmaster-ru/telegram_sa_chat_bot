from typing import AsyncIterable

from dishka import Provider, provide_all, provide, Scope
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine

from axiomai.application.interactors.buy_leads.buy_leads import BuyLeads
from axiomai.application.interactors.buy_leads.cancel_payment import CancelPayment
from axiomai.application.interactors.buy_leads.confirm_payment import ConfirmPayment
from axiomai.application.interactors.create_cabinet import CreateCabinet
from axiomai.application.interactors.create_cashback_table import CreateCashbackTable
from axiomai.application.interactors.create_user import CreateSeller
from axiomai.application.interactors.buy_leads.mark_payment_waiting_confirm import MarkPaymentWaitingConfirm
from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.config import Config
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.google_sheets import GoogleSheetsGateway
from axiomai.infrastructure.message_debouncer import MessageDebouncer
from axiomai.infrastructure.openai import OpenAIGateway


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_engine(self, config: Config) -> AsyncIterable[AsyncEngine]:
        engine = create_async_engine(
            config.postgres_uri,
            pool_size=15,
            max_overflow=15,
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


class CommonProvider(Provider):
    @provide(scope=Scope.APP)
    def get_message_debouncer(self, redis: Redis, config: Config) -> MessageDebouncer:
        return MessageDebouncer(
            redis=redis,
            delay_seconds=config.message_debounce_delay,
            ttl_seconds=config.message_accumulation_ttl,
            immediate_processing_length=config.immediate_processing_length,
        )


class GatewaysProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def get_tm(self, session: AsyncSession) -> TransactionManager:
        return session  # type: ignore[return-value]

    google_sheets_gateway = provide(GoogleSheetsGateway, scope=Scope.APP)
    openai_gateway = provide(OpenAIGateway, scope=Scope.APP)

    gateways = provide_all(CabinetGateway, CashbackTableGateway, PaymentGateway, UserGateway)


class TgbotInteractorsProvider(Provider):
    interactors = provide_all(
        CreateSeller,
        CreateCabinet,
        CreateCashbackTable,
        BuyLeads,
        MarkPaymentWaitingConfirm,
        ConfirmPayment,
        CancelPayment,
        scope=Scope.REQUEST,
    )


class ObserverInteractorsProvider(Provider):
    interactors = provide_all(
        ObserveCashbackTables,
        scope=Scope.REQUEST,
    )
