from aiogram import types
from aiogram.filters import  Command
from aiogram.fsm.context import FSMContext

from .router import router
from src.core.config import constants

# reset command for admins
@router.business_message(Command('reset'))
async def reset_admin(
    message: types.Message,
    state: FSMContext
):
    telegram_id = message.from_user.id
    if telegram_id in constants.ADMIN_ID_LIST:
        await state.clear()
        await message.answer("bot reseted!")
