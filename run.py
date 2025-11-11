import asyncio
from aiogram import Bot, Dispatcher

from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as asyncredis

from src.bot import (
    text_router, 
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
from src.core.config import settings

async def main():


    redis = await asyncredis.from_url(settings.REDIS_URL)
    storage = RedisStorage(redis) 
    
    spreadsheet = GoogleSheetClass(
        service_account_json=settings.SERVICE_ACCOUNT_JSON_STR, 
        table_url=settings.GOOGLE_SHEETS_URL_STR,
        buyers_sheet_name=settings.BUYERS_SHEET_NAME_STR,
        redis_client=redis,
        REDIS_KEY_USER_ROW_POSITION_STRING=settings.REDIS_KEY_USER_ROW_POSITION_STRING,
        REDIS_KEY_NM_IDS_ORDERED_LIST=settings.REDIS_KEY_NM_IDS_ORDERED_LIST
    )
    
    # загружаем упорядоченный список артикулов для кэшбека из google_sheets в redis
    await spreadsheet.load_nm_ids_ordered_list_into_redis(
        sheet_name=settings.ARTICLES_SHEET_STR,
        REDIS_KEY_NM_IDS_ORDERED_LIST=settings.REDIS_KEY_NM_IDS_ORDERED_LIST,
    )


    instruction_template = await spreadsheet.get_instruction_template(settings.INSTRUCTION_SHEET_NAME_STR)
    
    client_gpt_5 = OpenAiRequestClass(
        OPENAI_API_KEY=settings.OPENAI_TOKEN_STR, 
        GPT_MODEL_NAME_STR=settings.GPT_MODEL_NAME_STR, 
        PROXY=settings.PROXY,
        instruction_template=instruction_template,
        max_tokens=settings.GPT_MAX_TOKENS,
        temperature=settings.GPT_TEMPERATURE
    )

    # ============ START =============
    bot = Bot(token=settings.TG_BOT_TOKEN_STR)
    dp = Dispatcher(storage=storage)
    
    # Подключаем middleware и передаём готовое подключение
    middleware_check_redis = CheckRedisUserMiddleware(redis, settings.REDIS_KEY_SET_TELEGRAM_IDS)
    dp.business_message.middleware(middleware_check_redis)
    dp.callback_query.middleware(middleware_check_redis)

    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update(
        {
            "WB_TOKEN": settings.WB_TOKEN_STR,
            "spreadsheet": spreadsheet,
            "BUYERS_SHEET_NAME": settings.BUYERS_SHEET_NAME_STR,
            "INSTRUCTION_SHEET_NAME": settings.INSTRUCTION_SHEET_NAME_STR,
            "CHANNEL_USERNAME": settings.CHANNEL_USERNAME_STR,
            "ADMIN_ID_LIST": settings.ADMIN_ID_LIST,
            "client_gpt_5": client_gpt_5,
            "redis": redis,
            "REDIS_KEY_NM_IDS_ORDERED_LIST": settings.REDIS_KEY_NM_IDS_ORDERED_LIST,
            "REDIS_KEY_NM_IDS_REMAINS_HASH": settings.REDIS_KEY_NM_IDS_REMAINS_HASH,
            "REDIS_KEY_NM_IDS_TITLES_HASH": settings.REDIS_KEY_NM_IDS_TITLES_HASH
        }
    )
    #роутер, который ловит все текстовые сообщения
    dp.include_router(text_router)
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