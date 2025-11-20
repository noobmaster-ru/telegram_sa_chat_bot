import logging
from pathlib import Path
from aiogram import F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery

from src.db.models import CabinetORM
from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.string_converter_class import StringConverter
from src.core.config import constants, settings

from .router import router

# SELLER_MENU_TEXT[0] == '⚙️Добавить кабинет'
@router.message(F.text == constants.SELLER_MENU_TEXT[0], StateFilter(SellerStates.waiting_for_tap_to_menu))
async def add_cabinet(
    message: Message,
    state: FSMContext
):
    await message.answer(
        text=f'Сделайте себе копию этой таблицы\n\n {constants.GOOGLE_SHEETS_TEMPLATE_URL}\n\n и пришлите мне ссылку на неё',
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(SellerStates.waiting_for_new_google_sheets_url)
    
@router.message(
    F.text.startswith('http'), 
    StateFilter(SellerStates.waiting_for_new_google_sheets_url)
)
async def handle_gs_url(
    message: Message,
    state: FSMContext,
):
    google_sheets_url = message.text if message.text else "-"
    await state.update_data(
        google_sheets_url=google_sheets_url
    )
    await message.answer(
        f"Это  ваша ссылка на таблицу?:\n\n {google_sheets_url}",
        reply_markup=get_yes_no_keyboard(
            callback_prefix="gs_url",
            statement="cсылка на google sheets"
        )
    )
    await state.set_state(SellerStates.waiting_for_tap_to_keyboard_gs)


@router.callback_query(F.data.startswith("gs_url_") , StateFilter(SellerStates.waiting_for_tap_to_keyboard_gs))
async def callback_gs_url(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.data == "gs_url_yes":   
        await callback.message.edit_text("Теперь отправьте название вашего бренда на ВБ")
        await state.set_state(SellerStates.waiting_for_brand_name)
    else:
        await callback.message.edit_text("Хорошо, отправьте тогда ссылку ещё раз")
        await state.set_state(SellerStates.waiting_for_new_google_sheets_url)


@router.message(StateFilter(SellerStates.waiting_for_new_google_sheets_url))
async def waiting_for_gs_url(message: Message):
    await message.answer("Пожалуйста, пришлите ссылку на гугл-таблицу(без других слов)")


@router.message(StateFilter(SellerStates.waiting_for_tap_to_keyboard_gs))
async def waiting_for_tap_to_keyboard_gs(message: Message):
    await message.answer("Пожалуйста, нажмите на кнопку выше.")
