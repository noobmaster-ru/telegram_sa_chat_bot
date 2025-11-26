import logging
from aiogram.filters import StateFilter
from aiogram.types import Message

from src.bot.states.seller import SellerStates
from .router import router

# catch upexpected text from seller
@router.message(StateFilter(SellerStates.waiting_for_tap_to_menu))
async def waiting_for_tap_to_menu(message: Message):
    await message.answer("Пожалуйста, выберите пункт в меню и продолжим.")
