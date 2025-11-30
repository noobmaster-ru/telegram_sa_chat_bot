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

from src.bot.middlewares.ignore_bussiness_messages import IgnoreBusinessMessagesMiddleware
from src.bot.middlewares.media_group import MediaGroupMiddleware
from src.bot.middlewares.cabinet_context import CabinetContextMiddleware

from src.core.config import settings, constants

from src.db.base import on_shutdown, on_startup

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
    
    
    # spreadsheet = GoogleSheetClass(
    #     service_account_json=settings.SERVICE_ACCOUNT_AXIOMAI, 
    #     table_url=settings.GOOGLE_SHEETS_URL,
    #     buyers_sheet_name=constants.BUYERS_SHEET_NAME_STR,
    #     redis_client=redis_client,
    #     REDIS_KEY_USER_ROW_POSITION_STRING=constants.REDIS_KEY_USER_ROW_POSITION_STRING,
    #     REDIS_KEY_NM_IDS_ORDERED_LIST=constants.REDIS_KEY_NM_IDS_ORDERED_LIST
    # )
    
    # instruction_template = await spreadsheet.get_instruction_template(constants.INSTRUCTION_SHEET_NAME_STR)
    instruction_template = "..."  # поставь свою реализацию

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
    
    # Регистрируем хуки БД (они заполнят dp.workflow_data["db_session_factory"])
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # === MIDDLEWARES ===
    
    # 1) групповые медиа
    dp.business_message.middleware(MediaGroupMiddleware(latency=0.5))

    # 2) игнор сообщений от менеджера (бизнес-аккаунта)
    middleware_ignore_bussiness_messages = IgnoreBusinessMessagesMiddleware()
    dp.business_message.middleware(middleware_ignore_bussiness_messages)
    dp.callback_query.middleware(middleware_ignore_bussiness_messages)
    
    # 3) НОВЫЙ middleware: подставляем cabinet + spreadsheet по business_connection_id
    cabinet_ctx_middleware = CabinetContextMiddleware(
        redis_client=redis_client,
        service_account_json=settings.SERVICE_ACCOUNT_AXIOMAI,
        buyers_sheet_name=constants.BUYERS_SHEET_NAME_STR,
        REDIS_KEY_USER_ROW_POSITION_STRING=constants.REDIS_KEY_USER_ROW_POSITION_STRING
    )
    dp.business_message.middleware(cabinet_ctx_middleware)
    dp.callback_query.middleware(cabinet_ctx_middleware)

    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update(
        {
            # "spreadsheet": spreadsheet,
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