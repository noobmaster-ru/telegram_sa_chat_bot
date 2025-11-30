import asyncio
import redis.asyncio as asyncredis

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from src.bot.utils.inactivity_checker import inactivity_checker

from src.bot.handlers.clients.text_messages import router as text_router
from src.bot.handlers.clients.quiz import router as quiz_router 
from src.bot.handlers.clients.photo import router as photo_router
from src.bot.handlers.clients.payment_details import router as payment_router

from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass

from src.bot.middlewares.check_redis_telegram_id import CheckRedisUserMiddleware
from src.bot.middlewares.ignore_bussiness_messages import IgnoreBusinessMessagesMiddleware
from src.bot.middlewares.media_group import MediaGroupMiddleware

from src.core.config import settings, constants


async def main():
    # Один Redis-клиент, одна DB (например /0)
    redis_client = await asyncredis.from_url(settings.REDIS_URL)
    

    clients_storage = RedisStorage(
        redis=redis_client,
        key_builder=DefaultKeyBuilder(
            with_bot_id=True,
            with_business_connection_id=True,   # вот это главное - каждая связка "чат-бот <-> бизнес-акк" уникальна
            # опционально:
            # with_destiny=True,  # если будешь использовать разные destiny для сложных сценариев
        ),
    )
    
    
    spreadsheet = GoogleSheetClass(
        service_account_json=settings.SERVICE_ACCOUNT_AXIOMAI, 
        table_url=settings.GOOGLE_SHEETS_URL,
        buyers_sheet_name=constants.BUYERS_SHEET_NAME_STR,
        redis_client=redis_client,
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
    bot = Bot(token=settings.CLIENTS_BOT_TOKEN)
    dp = Dispatcher(storage=clients_storage)
    
    # middlewate to skip media_group(many photos in one message)
    dp.business_message.middleware(MediaGroupMiddleware(latency=0.5))

    # middlerware to check is user in redis store
    middleware_check_redis = CheckRedisUserMiddleware(redis_client, constants.REDIS_KEY_SET_TELEGRAM_IDS)
    dp.business_message.middleware(middleware_check_redis)
    dp.callback_query.middleware(middleware_check_redis)
    
    # middleware to ignore messages from us(manager) from bussiness account (BUSSINESS_ACCOUNTS_IDS)
    middleware_ignore_bussiness_messages = IgnoreBusinessMessagesMiddleware()
    dp.business_message.middleware(middleware_ignore_bussiness_messages)
    dp.callback_query.middleware(middleware_ignore_bussiness_messages)
    

    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update(
        {
            "spreadsheet": spreadsheet,
            "BUYERS_SHEET_NAME": constants.BUYERS_SHEET_NAME_STR,
            "INSTRUCTION_SHEET_NAME": constants.INSTRUCTION_SHEET_NAME_STR,
            "ADMIN_ID_LIST": constants.ADMIN_ID_LIST,
            "client_gpt_5": client_gpt_5,
            "redis": redis_client
        }
    )
    # check last time activity and send reminder message if user too late inactive
    asyncio.create_task(inactivity_checker(bot, dp.storage))
    

    # clients routers
    dp.include_routers(text_router, quiz_router, photo_router, payment_router) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())