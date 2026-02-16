import secrets
import uuid
from collections.abc import AsyncIterable
from datetime import datetime
from random import randint
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot
from aiogram.fsm.storage.base import BaseStorage
from aiogram_dialog.test_tools.memory_storage import JsonMemoryStorage
from alembic.command import upgrade
from dishka import make_async_container
from mimesis import Locale, Generic
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from testcontainers.postgres import PostgresContainer
from alembic.config import Config as AlembicConfig

from axiomai.config import Config
from axiomai.infrastructure.database.models import Cabinet, CashbackTable, Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus, CashbackArticle
from axiomai.infrastructure.database.models.user import User
from axiomai.infrastructure.google_sheets import GoogleSheetsGateway
from axiomai.infrastructure.message_debouncer import MessageDebouncer
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.superbanking import Superbanking
from tests.e2e.mocks import MocksProvider, FakeMessageDebouncer


class FakeRedis:
    """Fake Redis for testing that stores data in memory."""

    def __init__(self):
        self._data: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes | None:
        return self._data.get(key)

    async def set(self, key: str, value: str | bytes) -> None:
        if isinstance(value, str):
            value = value.encode()
        self._data[key] = value

    async def setex(self, key: str, ttl: int, value: str | bytes) -> None:
        await self.set(key, value)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)


@pytest.fixture(scope="session")
def postgres_uri():
    postgres = PostgresContainer("postgres:16-alpine")

    try:
        postgres.start()
        database_uri = postgres.get_connection_url(host="127.0.0.1", driver="psycopg")
        yield database_uri
    finally:
        postgres.stop()


@pytest.fixture(scope="session")
def alembic_config(postgres_uri: str):
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_uri)
    return alembic_cfg


@pytest.fixture(scope="session", autouse=True)
def upgrade_schema_db(alembic_config: AlembicConfig):
    upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
async def engine(postgres_uri: str):
    engine = create_async_engine(postgres_uri)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine) -> AsyncIterable[AsyncSession]:
    _session = AsyncSession(bind=engine, autoflush=False, expire_on_commit=False)
    yield _session
    await _session.rollback()


@pytest.fixture
async def di_container(session):
    google_sheets_mock = AsyncMock()
    google_sheets_mock.sync_buyers_to_sheet = AsyncMock()
    config = MagicMock()
    config.delay_between_bot_messages = 0

    container = make_async_container(
        MocksProvider(),
        context={
            AsyncSession: session,
            GoogleSheetsGateway: google_sheets_mock,
            Bot: AsyncMock(),
            OpenAIGateway: AsyncMock(),
            Config: config,
            MessageDebouncer: FakeMessageDebouncer(),
            Redis: FakeRedis(),
            BaseStorage: JsonMemoryStorage(),
            Superbanking: MagicMock(),
        },
    )
    yield container
    await container.close()


generic = Generic(locale=Locale.EN)


@pytest.fixture
def user_factory(session):
    async def get_user() -> User:
        user = User(
            telegram_id=randint(1, 1_000_000_000),
            user_name=generic.person.username(),
            fullname=generic.person.full_name(),
        )

        session.add(user)
        await session.flush()
        return user

    return get_user


@pytest.fixture
def cabinet_factory(session, user_factory):
    async def get_cabinet(
        user_id: int | None = None,
        balance: int = 0,
        initial_balance: int = 0,
        leads_balance: int = 1000,
        business_connection_id: str | None = None,
        is_superbanking_connect: bool = False,
    ) -> Cabinet:
        if not user_id:
            user = await user_factory()
            user_id = user.id

        cabinet = Cabinet(
            user_id=user_id,
            leads_balance=leads_balance,
            balance=balance,
            initial_balance=initial_balance,
            organization_name="none",
            link_code=secrets.token_urlsafe(16),
            business_connection_id=business_connection_id,
            is_superbanking_connect=is_superbanking_connect,
        )
        session.add(cabinet)
        await session.flush()
        return cabinet

    return get_cabinet


@pytest.fixture
def cashback_table_factory(session, cabinet_factory):
    async def get_cashback_table(
        cabinet_id: int | None = None, status: CashbackTableStatus = CashbackTableStatus.NEW
    ) -> CashbackTable:
        if not cabinet_id:
            cabinet = await cabinet_factory()
            cabinet_id = cabinet.id

        cashback_table = CashbackTable(cabinet_id=cabinet_id, table_id=str(uuid.uuid4()), status=status)
        session.add(cashback_table)
        await session.flush()
        return cashback_table

    return get_cashback_table


@pytest.fixture
def cashback_article_factory(session, cabinet_factory):
    async def get_cashback_article(cabinet_id: int | None = None, *, in_stock: bool = True) -> CashbackArticle:
        if not cabinet_id:
            cabinet = await cabinet_factory()
            cabinet_id = cabinet.id

        article = CashbackArticle(
            cabinet_id=cabinet_id,
            nm_id=randint(1, 1_000_000),
            title="Test Article",
            brand_name="Test Brand",
            image_url="http://example.com/image.jpg",
            instruction_text="Test Instruction",
            in_stock=in_stock,
        )
        session.add(article)
        await session.flush()
        return article

    return get_cashback_article


@pytest.fixture
def buyer_factory(session, cabinet_factory):
    async def get_buyer(
        cabinet_id: int | None = None,
        is_ordered: bool = False,
        is_left_feedback: bool = False,
        is_cut_labels: bool = False,
        phone_number: str | None = None,
        bank: str | None = None,
        amount: int | None = None,
        chat_history: list[dict] | None = None,
        updated_at: datetime | None = None,
    ) -> Buyer:
        if not cabinet_id:
            cabinet = await cabinet_factory()
            cabinet_id = cabinet.id

        buyer = Buyer(
            cabinet_id=cabinet_id,
            username="test_user",
            fullname="Test User",
            telegram_id=123456789,
            nm_id=777,
            is_ordered=is_ordered,
            is_left_feedback=is_left_feedback,
            is_cut_labels=is_cut_labels,
            phone_number=phone_number,
            bank=bank,
            amount=amount,
            chat_history=chat_history if chat_history is not None else [{"role": "user", "text": "hi"}],
        )
        session.add(buyer)
        await session.flush()

        if updated_at:
            buyer.updated_at = updated_at
            await session.flush()

        return buyer

    return get_buyer