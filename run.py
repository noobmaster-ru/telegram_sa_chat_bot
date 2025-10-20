from aiogram import Bot, Dispatcher
import asyncio
import os 
from dotenv import load_dotenv

from handlers import router
from database import init_db

from google_sheets_class import GoogleSheetClass

async def main():
    load_dotenv()
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN_STR")
    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
    GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL")
    SHEET_NAME = os.getenv("SHEET_NAME")

    init_db()  # создаём таблицу при старте
    spreadsheet_object = GoogleSheetClass(SERVICE_ACCOUNT_JSON, GOOGLE_SHEETS_URL)
    nm_id = spreadsheet_object.get_article(SHEET_NAME)


    bot = Bot(token=TG_BOT_TOKEN)
    dp = Dispatcher()
    
    # добавляем артикул в глобальные данные - чтобы все хэндлеры его видели
    dp.workflow_data.update({"nm_id": nm_id})
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())