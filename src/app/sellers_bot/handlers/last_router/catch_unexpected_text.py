import logging
from aiogram.filters import StateFilter
from aiogram.types import Message

from src.app.bot.states.seller import SellerStates
from src.tools.string_converter_class import StringConverter

from .router import router

# catch upexpected text from seller
@router.message(StateFilter(SellerStates.waiting_for_tap_to_menu))
async def waiting_for_tap_to_menu(message: Message):
    text = "Пожалуйста, выберите пункт в меню и продолжим."
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )
