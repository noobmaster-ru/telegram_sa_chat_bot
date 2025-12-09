import asyncio
import redis.asyncio as asyncredis

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from src.app.clients_bot.handlers.text_messages import router as text_router
from src.app.clients_bot.handlers.quiz import router as quiz_router 
from src.app.clients_bot.handlers.photo import router as photo_router
from src.app.clients_bot.handlers.payment_details import router as payment_router

from src.app.bot.utils.inactivity_checker import inactivity_checker

from src.app.bot.middlewares.ignore_bussiness_messages import IgnoreBusinessMessagesMiddleware
from src.app.bot.middlewares.media_group import MediaGroupMiddleware
from src.app.bot.middlewares.cabinet_context import CabinetContextMiddleware
from src.app.bot.middlewares.check_old_users import CheckUserInOldUsers

from src.infrastructure.db.base import on_shutdown, on_startup

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
    
    # ============ START =============
    bot = Bot(token=settings.CLIENTS_BOT_TOKEN)
    dp = Dispatcher(storage=clients_storage)
    
    # Регистрируем хуки БД (они заполнят dp.workflow_data["db_session_factory"])
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # === MIDDLEWARES ===
    # 0) старые юзеры, которые писали бизнес-акку до подключения бота
    dp.business_message.middleware(CheckUserInOldUsers(redis=redis_client))
    
    # 1) групповые медиа
    dp.business_message.middleware(MediaGroupMiddleware(latency=0.5))

    # 2) игнор сообщений от менеджера (бизнес-аккаунта)
    middleware_ignore_bussiness_messages = IgnoreBusinessMessagesMiddleware(redis_client=redis_client)
    dp.business_message.middleware(middleware_ignore_bussiness_messages)
    dp.callback_query.middleware(middleware_ignore_bussiness_messages)
    
    # 3) НОВЫЙ middleware: подставляем cabinet + spreadsheet + client_gpt_5 по business_connection_id
    cabinet_ctx_middleware = CabinetContextMiddleware(
        redis_client=redis_client,
        service_account_json=settings.SERVICE_ACCOUNT_AXIOMAI,
        buyers_sheet_name=constants.BUYERS_SHEET_NAME_STR,
        REDIS_KEY_USER_ROW_POSITION_STRING=constants.REDIS_KEY_USER_ROW_POSITION_STRING,
        openai_api_key=settings.OPENAI_TOKEN, 
        gpt_model_name=constants.GPT_MODEL_NAME, 
        gpt_model_name_photo=constants.GPT_MODEL_NAME_PHOTO_ANALYSIS,
        proxy=settings.PROXY,
        max_tokens=constants.GPT_MAX_TOKENS,
        max_output_tokens_photo=constants.GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
        temperature=constants.GPT_TEMPERATURE,
        reasoning=constants.GPT_REASONING,
        block_if_no_leads=True,   # включаем блокировку, если селлер не купил лиды
    )
    dp.business_message.middleware(cabinet_ctx_middleware)
    dp.callback_query.middleware(cabinet_ctx_middleware)

    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update({"redis": redis_client})
    
    # check last time activity and send reminder message if user too late inactive
    asyncio.create_task(inactivity_checker(bot, dp.storage))
    

    # clients routers
    dp.include_routers(text_router, quiz_router, photo_router, payment_router) 
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())