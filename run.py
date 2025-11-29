import asyncio
from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as asyncredis
from src.bot.utils.inactivity_checker import inactivity_checker
# from src.bot.utils.is_subscribe_checking import google_sheets_sub_updater

from src.bot.handlers.clients.text_messages import router as text_router
from src.bot.handlers.clients.quiz import router as quiz_router 
from src.bot.handlers.clients.photo import router as photo_router
from src.bot.handlers.clients.payment_details import router as payment_router

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
    storage = RedisStorage(redis) 
    
    spreadsheet = GoogleSheetClass(
        service_account_json=settings.SERVICE_ACCOUNT_AXIOMAI, 
        table_url=settings.GOOGLE_SHEETS_URL,
        buyers_sheet_name=constants.BUYERS_SHEET_NAME_STR,
        redis_client=redis,
        REDIS_KEY_USER_ROW_POSITION_STRING=constants.REDIS_KEY_USER_ROW_POSITION_STRING,
        REDIS_KEY_NM_IDS_ORDERED_LIST=constants.REDIS_KEY_NM_IDS_ORDERED_LIST
    )
    
    instruction_template = await spreadsheet.get_instruction_template(constants.INSTRUCTION_SHEET_NAME_STR)
    
    client_gpt_5 = OpenAiRequestClass(
        OPENAI_API_KEY=settings.OPENAI_TOKEN, 
        GPT_MODEL_NAME=constants.GPT_MODEL_NAME, 
        GPT_MODEL_NAME_PHOTO_ANALYSIS=constants.GPT_MODEL_NAME_PHOTO_ANALYSIS,
        PROXY=settings.PROXY,
        instruction_template=instruction_template,
        max_tokens=constants.GPT_MAX_TOKENS,
        max_output_tokens_photo_analysis= constants.GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
        temperature=constants.GPT_TEMPERATURE,
        reasoning=constants.GPT_REASONING
    )

    # ============ START =============
    bot = Bot(token=settings.TG_BOT_TOKEN)
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
            "WB_TOKEN": settings.WB_TOKEN,
            "spreadsheet": spreadsheet,
            "BUYERS_SHEET_NAME": constants.BUYERS_SHEET_NAME_STR,
            "INSTRUCTION_SHEET_NAME": constants.INSTRUCTION_SHEET_NAME_STR,
            "CHANNEL_USERNAME": constants.CHANNEL_USERNAME_STR,
            "ADMIN_ID_LIST": constants.ADMIN_ID_LIST,
            "client_gpt_5": client_gpt_5,
            "redis": redis,
            "REDIS_KEY_NM_IDS_ORDERED_LIST": constants.REDIS_KEY_NM_IDS_ORDERED_LIST,
            "REDIS_KEY_NM_IDS_REMAINS_HASH": constants.REDIS_KEY_NM_IDS_REMAINS_HASH,
            "REDIS_KEY_NM_IDS_TITLES_HASH": constants.REDIS_KEY_NM_IDS_TITLES_HASH
        }
    )
    # check last time activity and send reminder message if user too late inactive
    asyncio.create_task(inactivity_checker(bot, dp.storage))
    
    # check subscribtion to channel for all users in google sheets
    # asyncio.create_task(google_sheets_sub_updater(bot, spreadsheet))
    
    # clients routers
    dp.include_routers(text_router, quiz_router, photo_router, payment_router) 
    
    # seller routers 
    dp.include_routers(start_router, add_cabinet_router, delete_cabinet_router, view_cabinets_router, add_nm_id_router, last_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())