from aiogram import Bot, Dispatcher
import asyncio
import os 
from dotenv import load_dotenv

from handlers import message_router, agreement_router, question_router, subscribtion_router, photo_router , requisites_router
from google_sheets.google_sheets_class import GoogleSheetClass

async def main():
    load_dotenv()
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN_STR")
    SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON_STR")
    GOOGLE_SHEETS_URL = os.getenv("GOOGLE_SHEETS_URL_STR")
    
    LOWER_LIMIT_OF_MESSAGE_LENGTH = int(os.getenv("LOWER_LIMIT_OF_MESSAGE_LENGTH_INT"))
    ARTICLES_SHEET = os.getenv("ARTICLES_SHEET_STR")
    INSTRUCTION_SHEET_NAME = os.getenv("INSTRUCTION_SHEET_NAME_STR")
    BUYERS_SHEET_NAME = os.getenv("BUYERS_SHEET_NAME_STR")

    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME_STR")  # username канала

    
    spreadsheet = GoogleSheetClass(SERVICE_ACCOUNT_JSON, GOOGLE_SHEETS_URL)
    nm_id = spreadsheet.get_nm_id(ARTICLES_SHEET)
    instruction_str = spreadsheet.get_instruction(INSTRUCTION_SHEET_NAME, nm_id)

    bot = Bot(token=TG_BOT_TOKEN)
    dp = Dispatcher()
    
    ADMIN_ID_LIST = [694144143, 547299317]
    # добавляем глобальные данные - чтобы все хэндлеры видели их
    dp.workflow_data.update(
        {
            "instruction_str": instruction_str,
            "LOWER_LIMIT_OF_MESSAGE_LENGTH": LOWER_LIMIT_OF_MESSAGE_LENGTH,
            "spreadsheet": spreadsheet,
            "BUYERS_SHEET_NAME": BUYERS_SHEET_NAME,
            "nm_id": nm_id,
            "CHANNEL_USERNAME": CHANNEL_USERNAME,
            "ADMIN_ID_LIST": ADMIN_ID_LIST
        }
    )
    # сначала поставим роутер, который ловит текстовые сообщения-реквизиты
    dp.include_router(requisites_router)
    # и затем только роутер, который ловит все текстовые сообщения
    dp.include_router(message_router)
    
    dp.include_router(question_router)
    dp.include_router(agreement_router)
    dp.include_router(subscribtion_router)
    dp.include_router(photo_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())