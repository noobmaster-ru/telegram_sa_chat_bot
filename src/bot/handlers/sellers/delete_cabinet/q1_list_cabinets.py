# import logging
# from pathlib import Path
# from aiogram import F, Bot
# from aiogram.filters import StateFilter
# from aiogram.fsm.context import FSMContext
# from sqlalchemy.ext.asyncio import async_sessionmaker
# from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery

# from src.db.models import CabinetORM
# from src.bot.states.seller import SellerStates
# from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
# from src.services.string_converter_class import StringConverter
# from src.core.config import constants, settings
# from src.bot.keyboards.reply.menu import kb_menu

# from .router import router

# # SELLER_MENU_TEXT[1] == '❌Удалить кабинет'
# @router.message(F.text == constants.SELLER_MENU_TEXT[1], StateFilter(SellerStates.waiting_for_tap_to_menu))
# async def delete_cabinet(message: Message):
#     await message.answer(
#         "Пока не реализовал",
#         reply_markup=kb_menu
#     )