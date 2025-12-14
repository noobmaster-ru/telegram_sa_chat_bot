from aiogram import  F
from aiogram.filters import Command
from aiogram.types import Message

from src.core.config import constants
from src.tools.string_converter_class import StringConverter

from .router import router

# Команда /support работает в любом состоянии
@router.message(Command("support"))
@router.message(F.text == constants.SELLER_MENU_TEXT[4]) # 4 - поддержка
async def seller_support(message: Message):
    text = (
        f"Напишите, пожалуйста, {constants.ADMIN_USERNAME}, поможем.\n\n"
        "К сообщению можно прикрепить скриншоты, чтобы быстрее разобраться."
    )
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
    )