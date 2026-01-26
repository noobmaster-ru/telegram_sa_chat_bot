import secrets
import uuid
from collections.abc import AsyncIterable
from random import randint
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot
from alembic.command import upgrade
from dishka import make_async_container
from mimesis import Locale, Generic
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from testcontainers.postgres import PostgresContainer
from alembic.config import Config as AlembicConfig

from axiomai.config import Config
from axiomai.infrastructure.database.models import Cabinet, CashbackTable
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.database.models.user import User
from axiomai.infrastructure.google_sheets import GoogleSheetsGateway
from axiomai.infrastructure.openai import OpenAIGateway
from tests.e2e.mocks import MocksProvider


@pytest.fixture(scope="session")
def postgres_uri():
    postgres = PostgresContainer("postgres:16-alpine")

    try:
        postgres.start()
        database_uri = postgres.get_connection_url(driver="psycopg")
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
    container = make_async_container(
        MocksProvider(),
        context={
            AsyncSession: session,
            GoogleSheetsGateway: AsyncMock(),
            Bot: AsyncMock(),
            OpenAIGateway: AsyncMock(),
            Config: MagicMock(),
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
    async def get_cabinet(user_id: int | None = None, leads_balance: int = 0) -> Cabinet:
        if not user_id:
            user = await user_factory()
            user_id = user.id

        cabinet = Cabinet(
            user_id=user_id,
            leads_balance=leads_balance,
            organization_name="none",
            link_code=secrets.token_urlsafe(16),
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
