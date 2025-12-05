from aiogram import types
from aiogram.filters import  Command
from aiogram.fsm.context import FSMContext

from src.core.config import constants
from src.tools.string_converter_class import StringConverter
from .router import router

# reset command for admins
@router.business_message(Command('reset'))
async def reset_admin(
    message: types.Message,
    state: FSMContext
):
    telegram_id = message.from_user.id
    if telegram_id in constants.ADMIN_ID_LIST:
        text = "bot reseted"
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
