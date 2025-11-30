import asyncio
from src.db.base import async_engine, Base

async def init_db():
    async with async_engine.begin() as conn:
        async_engine.echo = True
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("DB schema created")

if __name__ == "__main__":
    asyncio.run(init_db())