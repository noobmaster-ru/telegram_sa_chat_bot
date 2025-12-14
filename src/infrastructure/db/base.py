from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

from aiogram import Dispatcher

class Base(DeclarativeBase):
    pass


async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
    echo=True,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def on_startup(dispatcher: Dispatcher):
    async_engine.echo = True
    dispatcher.workflow_data["db_session_factory"] = async_session_factory
    print("[DB] connected")

async def on_shutdown(dispatcher: Dispatcher):
    await async_engine.dispose()
    print("[DB] disconnected")