from aiogram import types
from aiogram.filters import  Command
from aiogram.fsm.context import FSMContext

from dishka.integrations.aiogram import FromDishka

from src.services.google_sheets_class import GoogleSheetClass
from .router import router

# reset command for admins
@router.business_message(Command('reset'))
async def reset_admin(
    message: types.Message,
    spreadsheet: FromDishka[GoogleSheetClass],
    ADMIN_ID_LIST: list,
    state: FSMContext
):
    telegram_id = message.from_user.id
    if telegram_id in ADMIN_ID_LIST:
        await state.clear()
        await message.answer("bot reseted!")
