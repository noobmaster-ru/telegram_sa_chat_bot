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
    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON_STR")
    GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL_STR")
    
    LOWER_LIMIT_OF_MESSAGE_LENGTH = int(os.getenv("LOWER_LIMIT_OF_MESSAGE_LENGTH_INT"))
    ARTICLES_SHEET = os.getenv("ARTICLES_SHEET_STR")
    INSTRUCTION_SHEET_NAME = os.getenv("INSTRUCTION_SHEET_NAME_STR")
    BUYERS_SHEET_NAME = os.getenv("BUYERS_SHEET_NAME_STR")

    init_db()  # создаём таблицу при старте
    spreadsheet = GoogleSheetClass(SERVICE_ACCOUNT_JSON, GOOGLE_SHEETS_URL)
    
    nm_id = spreadsheet.get_nm_id(ARTICLES_SHEET)
    instruction_str = spreadsheet.get_instruction(INSTRUCTION_SHEET_NAME, nm_id)

    bot = Bot(token=TG_BOT_TOKEN)
    dp = Dispatcher()
    
    # добавляем артикул в глобальные данные - чтобы все хэндлеры его видели
    dp.workflow_data.update(
        {
            "instruction_str": instruction_str,
            "LOWER_LIMIT_OF_MESSAGE_LENGTH": LOWER_LIMIT_OF_MESSAGE_LENGTH,
            "spreadsheet": spreadsheet,
            "BUYERS_SHEET_NAME": BUYERS_SHEET_NAME,
            "nm_id": nm_id
        }
    )
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())