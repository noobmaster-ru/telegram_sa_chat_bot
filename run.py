import asyncio
from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as asyncredis
from src.bot.utils.inactivity_checker import inactivity_checker
from src.bot import (
    text_router, 
    quiz_router,
    photo_router, 
    requisites_router
)

from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass

from src.bot.middlewares.check_redis_telegram_id import CheckRedisUserMiddleware
from src.core.config import settings, constants

async def main():
    redis = await asyncredis.from_url(settings.REDIS_URL)
    storage = RedisStorage(redis) 
    
    spreadsheet = GoogleSheetClass(
        service_account_json=settings.SERVICE_ACCOUNT_JSON, 
        table_url=settings.GOOGLE_SHEETS_URL,
        buyers_sheet_name=constants.BUYERS_SHEET_NAME_STR,
        redis_client=redis,
        REDIS_KEY_USER_ROW_POSITION_STRING=constants.REDIS_KEY_USER_ROW_POSITION_STRING,
        REDIS_KEY_NM_IDS_ORDERED_LIST=constants.REDIS_KEY_NM_IDS_ORDERED_LIST
    )
    
    # загружаем упорядоченный список артикулов для кэшбека из google_sheets в redis
    await spreadsheet.load_nm_ids_ordered_list_into_redis(
        sheet_name=constants.ARTICLES_SHEET_STR,
        REDIS_KEY_NM_IDS_ORDERED_LIST=constants.REDIS_KEY_NM_IDS_ORDERED_LIST,
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
    
    # Подключаем middleware и передаём готовое подключение
    middleware_check_redis = CheckRedisUserMiddleware(redis, constants.REDIS_KEY_SET_TELEGRAM_IDS)
    dp.business_message.middleware(middleware_check_redis)
    dp.callback_query.middleware(middleware_check_redis)

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
    dp.include_router(text_router) # catch first and last text messages and get it to gpt
    dp.include_router(quiz_router) #  quiz - Yes/No questions
    dp.include_router(photo_router) # catch photos
    dp.include_router(requisites_router) # catch requisites
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())