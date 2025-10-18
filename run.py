from aiogram import Bot, Dispatcher
import asyncio
import os 
from dotenv import load_dotenv


from handlers import router
from database import init_db

async def main():
    load_dotenv()
    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN_STR")
     
    init_db()  # создаём таблицу при старте
    
    bot = Bot(token=TG_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())