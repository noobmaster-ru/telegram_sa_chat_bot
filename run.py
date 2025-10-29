import os 
import logging
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

logging.basicConfig(
    level=logging.INFO,
    filename="logs/bot.log",
    format="%(asctime)s [%(levelname)s] %(message)s",
)

async def main():
    load_dotenv()
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN_STR")
    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON_STR")
    GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL_STR")
    BUYERS_SHEET_NAME = os.getenv("BUYERS_SHEET_NAME_STR")
    
    spreadsheet = GoogleSheetClass(
        service_account_json=SERVICE_ACCOUNT_JSON, 
        table_url=GOOGLE_SHEETS_URL,
        buyers_sheet_name=BUYERS_SHEET_NAME
    )
    
    ARTICLES_SHEET = os.getenv("ARTICLES_SHEET_STR")
    INSTRUCTION_SHEET_NAME = os.getenv("INSTRUCTION_SHEET_NAME_STR")
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME_STR")  # username канала

    nm_id = await spreadsheet.get_nm_id(ARTICLES_SHEET)
    instruction_str = await spreadsheet.get_instruction(INSTRUCTION_SHEET_NAME, nm_id)

    # создаём экземпляр класса OpenAiRequestClass
    GPT_MODEL_NAME_STR = os.getenv("GPT_MODEL_NAME_STR")
    OPENAI_API_KEY = os.getenv("OPENAI_TOKEN_STR")
    PROXY = os.getenv("PROXY")
    MAX_TOKENS = int(os.getenv("GPT_MAX_TOKENS"))
    GPT_TEMPERATURE = float(os.getenv("GPT_TEMPERATURE"))
    
    client_gpt_5 = OpenAiRequestClass(
        OPENAI_API_KEY=OPENAI_API_KEY, 
        GPT_MODEL_NAME_STR=GPT_MODEL_NAME_STR, 
        PROXY=PROXY,
        instruction_str=instruction_str,
        max_tokens=MAX_TOKENS,
        temperature=GPT_TEMPERATURE
    )

    # Redis storage
    REDIS_URL = os.getenv("REDIS_URL")
    REDIS_KEY_SET_TELEGRAM_IDS = os.getenv("REDIS_KEY_SET_TELEGRAM_IDS")
    redis = await asyncredis.from_url(REDIS_URL)
    
    bot = Bot(token=TG_BOT_TOKEN)
    dp = Dispatcher(storage=RedisStorage(redis))
    
    ADMIN_ID_LIST = [694144143, 547299317]
    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update(
        {
            "instruction_str": instruction_str,
            "spreadsheet": spreadsheet,
            "BUYERS_SHEET_NAME": BUYERS_SHEET_NAME,
            "nm_id": nm_id,
            "CHANNEL_USERNAME": CHANNEL_USERNAME,
            "ADMIN_ID_LIST": ADMIN_ID_LIST,
            "client_gpt_5": client_gpt_5,
            "redis": redis,
            "REDIS_KEY_SET_USERS_ID": REDIS_KEY_SET_TELEGRAM_IDS
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