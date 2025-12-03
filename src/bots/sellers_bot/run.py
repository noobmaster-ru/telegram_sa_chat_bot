import asyncio
import redis.asyncio as asyncredis

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder


from src.bot.handlers.sellers.add_cabinet import router as add_cabinet_router
from src.bot.handlers.sellers.cmd_start import router as start_router
from src.bot.handlers.sellers.view_cabinets import router as view_cabinets_router
# from src.bot.handlers.sellers.delete_cabinet import router as delete_cabinet_router
from src.bot.handlers.sellers.last_router import router as last_router
# from src.bot.handlers.sellers.add_extra_nm_id import router as add_nm_id_router
from src.bot.handlers.sellers.buy_leads import router as buy_leads_router
from src.bot.handlers.sellers.my_article import router as my_article_router

from src.bot.middlewares.ignore_bussiness_messages import IgnoreBusinessMessagesMiddleware
from src.bot.middlewares.media_group import MediaGroupMiddleware

from src.db.base import on_shutdown, on_startup

from src.core.config import settings, constants

async def main():
    # Один Redis-клиент, одна DB (например /0)
    redis_client = await asyncredis.from_url(settings.REDIS_URL)
    
    sellers_storage = RedisStorage(
        redis=redis_client,
        key_builder=DefaultKeyBuilder(
            with_bot_id=True,  # чтобы ключи еще и по боту разделялись
        ),
    ) 
    # ============ START =============
    bot = Bot(token=settings.SELLERS_BOT_TOKEN)
    dp = Dispatcher(storage=sellers_storage)
    
    # middlewate to skip media_group(many photos in one message)
    dp.message.middleware(MediaGroupMiddleware(latency=0.5))
    
    # create poll connection to and close poll connection to db
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update({"redis": redis_client})
    
    # seller routers 
    dp.include_routers(start_router, add_cabinet_router, buy_leads_router, view_cabinets_router, my_article_router, last_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())