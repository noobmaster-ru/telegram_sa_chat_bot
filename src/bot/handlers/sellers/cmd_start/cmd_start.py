import logging
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from src.bot.keyboards.reply.menu import kb_menu
from src.db.models import UserORM
from src.bot.states.seller import SellerStates
from src.tools.string_converter_class import StringConverter

from .router import router


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
):
    telegram_id = message.from_user.id
    fullname = message.from_user.full_name 
    user_name = message.from_user.username

    await state.update_data(
        telegram_id=telegram_id,
        fullname=fullname,
        user_name=user_name
    )
    await message.answer(f"Здравствуйте!")

    text = "Скиньте ваш email(нужен для связи)"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        # reply_markup=kb_menu,
        parse_mode="MarkdownV2"
    )
    await state.set_state(SellerStates.email)
