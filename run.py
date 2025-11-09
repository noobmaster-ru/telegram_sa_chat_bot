import os 
# import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as asyncredis

from src.bot import (
    message_router, 
    agreement_router, 
    subscribtion_router, 
    photo_router , 
    requisites_router, 
    unexpected_text_router,
    order_router
)

from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass

from src.bot.middlewares.check_redis_telegram_id import CheckRedisUserMiddleware

async def main():
    load_dotenv()
    # Telegram
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN_STR")
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME_STR")  # username канала
    
    # Wildberries
    WB_TOKEN = os.getenv("WB_TOKEN_STR")
    # Redis storage
    REDIS_URL = os.getenv("REDIS_URL")
    REDIS_KEY_NM_IDS_ORDERED_LIST=os.getenv("REDIS_KEY_NM_IDS_ORDERED_LIST")
    REDIS_KEY_SET_TELEGRAM_IDS = os.getenv("REDIS_KEY_SET_TELEGRAM_IDS")
    REDIS_KEY_USER_ROW_POSITION_STRING = os.getenv("REDIS_KEY_USER_ROW_POSITION_STRING")
    REDIS_KEY_NM_IDS_REMAINS_HASH = os.getenv("REDIS_KEY_NM_IDS_REMAINS_HASH")
    REDIS_KEY_NM_IDS_TITLES_HASH = os.getenv("REDIS_KEY_NM_IDS_TITLES_HASH")
    
    redis = await asyncredis.from_url(REDIS_URL)
    storage = RedisStorage(redis) 
    

    # Google Sheets
    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON_STR")
    GOOGLE_SHEETS_URL_STR = os.getenv("GOOGLE_SHEETS_URL_STR")
    
    ARTICLES_SHEET = os.getenv("ARTICLES_SHEET_STR")
    BUYERS_SHEET_NAME = os.getenv("BUYERS_SHEET_NAME_STR")
    INSTRUCTION_SHEET_NAME = os.getenv("INSTRUCTION_SHEET_NAME_STR")
    
    spreadsheet = GoogleSheetClass(
        service_account_json=SERVICE_ACCOUNT_JSON, 
        table_url=GOOGLE_SHEETS_URL_STR,
        buyers_sheet_name=BUYERS_SHEET_NAME,
        redis_client=redis,
        REDIS_KEY_USER_ROW_POSITION_STRING=REDIS_KEY_USER_ROW_POSITION_STRING,
        REDIS_KEY_NM_IDS_ORDERED_LIST=REDIS_KEY_NM_IDS_ORDERED_LIST
    )
    # загружаем данные по артикулам из google_sheets в redis
    await spreadsheet.load_nm_ids_and_amounts_to_redis(
        ARTICLES_SHEET,
        REDIS_KEY_NM_IDS_ORDERED_LIST,
        REDIS_KEY_NM_IDS_REMAINS_HASH,
        REDIS_KEY_NM_IDS_TITLES_HASH
    )

    # Open AI
    GPT_MODEL_NAME_STR = os.getenv("GPT_MODEL_NAME_STR")
    OPENAI_API_KEY = os.getenv("OPENAI_TOKEN_STR")
    PROXY = os.getenv("PROXY")
    MAX_TOKENS = int(os.getenv("GPT_MAX_TOKENS"))
    GPT_TEMPERATURE = float(os.getenv("GPT_TEMPERATURE"))
    
    instruction_template = await spreadsheet.get_instruction_template(INSTRUCTION_SHEET_NAME)
    
    client_gpt_5 = OpenAiRequestClass(
        OPENAI_API_KEY=OPENAI_API_KEY, 
        GPT_MODEL_NAME_STR=GPT_MODEL_NAME_STR, 
        PROXY=PROXY,
        instruction_template=instruction_template,
        max_tokens=MAX_TOKENS,
        temperature=GPT_TEMPERATURE
    )

    # ============ START =============
    bot = Bot(token=TG_BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Подключаем middleware и передаём готовое подключение
    middleware_check_redis = CheckRedisUserMiddleware(redis, REDIS_KEY_SET_TELEGRAM_IDS)
    dp.business_message.middleware(middleware_check_redis)
    dp.callback_query.middleware(middleware_check_redis)


    ADMIN_ID_LIST = [694144143, 547299317]
    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update(
        {
            # "bot": bot,
            "WB_TOKEN": WB_TOKEN,
            "spreadsheet": spreadsheet,
            "BUYERS_SHEET_NAME": BUYERS_SHEET_NAME,
            "INSTRUCTION_SHEET_NAME": INSTRUCTION_SHEET_NAME,
            "CHANNEL_USERNAME": CHANNEL_USERNAME,
            "ADMIN_ID_LIST": ADMIN_ID_LIST,
            "client_gpt_5": client_gpt_5,
            "redis": redis,
            "REDIS_KEY_NM_IDS_ORDERED_LIST": REDIS_KEY_NM_IDS_ORDERED_LIST,
            "REDIS_KEY_NM_IDS_REMAINS_HASH": REDIS_KEY_NM_IDS_REMAINS_HASH,
            "REDIS_KEY_NM_IDS_TITLES_HASH": REDIS_KEY_NM_IDS_TITLES_HASH
        }
    )
    #роутер, который ловит все текстовые сообщения
    dp.include_router(message_router)
    # первые роутеры - с вопросами да/нет
    dp.include_router(photo_router)
    dp.include_router(unexpected_text_router)
    dp.include_router(order_router)

    
    #роутер, который ловит текстовые сообщения-реквизиты
    dp.include_router(requisites_router)
    
    
    dp.include_router(agreement_router)
    dp.include_router(subscribtion_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())