import asyncio
from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
import redis.asyncio as asyncredis
from src.bot.utils.inactivity_checker import inactivity_checker


from src.bot.handlers.sellers.add_cabinet import router as add_cabinet_router
from src.bot.handlers.sellers.cmd_start import router as start_router
from src.bot.handlers.sellers.view_cabinets import router as view_cabinets_router
from src.bot.handlers.sellers.delete_cabinet import router as delete_cabinet_router
from src.bot.handlers.sellers.last_router import router as last_router
from src.bot.handlers.sellers.add_extra_nm_id import router as add_nm_id_router

from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass

from src.bot.middlewares.check_redis_telegram_id import CheckRedisUserMiddleware
from src.bot.middlewares.ignore_bussiness_messages import IgnoreBusinessMessagesMiddleware
from src.bot.middlewares.media_group import MediaGroupMiddleware
from src.core.config import settings, constants
from src.db.base import on_shutdown, on_startup

async def main():
    redis = await asyncredis.from_url(settings.REDIS_URL)
    storage = RedisStorage(
        redis=redis,
        # key_builder=DefaultKeyBuilder(with_bot_id=True)
    ) 

    # ============ START =============
    bot = Bot(token=settings.TG_BOT_TOKEN_SELLERS)
    dp = Dispatcher(storage=storage)
    
    # middlewate to skip media_group(many photos in one message)
    dp.business_message.middleware(MediaGroupMiddleware(latency=0.5))

    # middlerware to check is user in redis store
    middleware_check_redis = CheckRedisUserMiddleware(redis, constants.REDIS_KEY_SET_TELEGRAM_IDS)
    dp.business_message.middleware(middleware_check_redis)
    dp.callback_query.middleware(middleware_check_redis)
    
    # middleware to ignore messages from us(manager) from bussiness account (BUSSINESS_ACCOUNTS_IDS)
    middleware_ignore_bussiness_messages = IgnoreBusinessMessagesMiddleware()
    dp.business_message.middleware(middleware_ignore_bussiness_messages)
    dp.callback_query.middleware(middleware_ignore_bussiness_messages)
    
    # create poll connection to and close poll connection to db
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update(
        {
            # "WB_TOKEN": settings.WB_TOKEN,
            "BUYERS_SHEET_NAME": constants.BUYERS_SHEET_NAME_STR,
            "INSTRUCTION_SHEET_NAME": constants.INSTRUCTION_SHEET_NAME_STR,
            "CHANNEL_USERNAME": constants.CHANNEL_USERNAME_STR,
            "ADMIN_ID_LIST": constants.ADMIN_ID_LIST,
            "redis": redis,
            "REDIS_KEY_NM_IDS_ORDERED_LIST": constants.REDIS_KEY_NM_IDS_ORDERED_LIST,
            "REDIS_KEY_NM_IDS_REMAINS_HASH": constants.REDIS_KEY_NM_IDS_REMAINS_HASH,
            "REDIS_KEY_NM_IDS_TITLES_HASH": constants.REDIS_KEY_NM_IDS_TITLES_HASH
        }
    )
    
    # seller routers 
    dp.include_routers(start_router, add_cabinet_router, delete_cabinet_router, view_cabinets_router, add_nm_id_router, last_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())