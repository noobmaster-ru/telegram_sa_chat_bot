import asyncio
from src.db.base import async_engine, Base

async def reset_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] reset done")

if __name__ == "__main__":
    asyncio.run(reset_db())