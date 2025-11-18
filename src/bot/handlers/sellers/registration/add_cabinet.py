import logging
from aiogram import  F
from aiogram.filters import StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.models import CabinetORM
from src.core.config import constants
from src.bot.states.seller import SellerStates
from src.core.config import constants
from .router import router

# SELLER_MENU_TEXT[0] == '⚙️Добавить кабинет'
@router.message(F.text == constants.SELLER_MENU_TEXT[0], StateFilter(SellerStates.waiting_for_tap_to_menu))
async def add_cabinet(
    message: Message,
    state: FSMContext
):
    await message.answer(
        f'Сделайте себе копию этой таблицы\n\n {constants.GOOGLE_SHEETS_TEMPLATE_URL}\n\n и пришлите мне ссылку на неё'
    )
    await state.set_state(SellerStates.waiting_for_new_google_sheets_url)



@router.message(StateFilter(SellerStates.waiting_for_cabinet_name))
async def handle_url(
    message: Message,
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    cabinet_name = message.text.strip()
    user_data = await state.get_data()
    
    google_sheets_url = user_data["google_sheets_url"]
    user_id = user_data["user_id"]
    
    await message.answer(f"Вот название для вашего кабинеты: {cabinet_name}")
    async with db_session_factory() as session:
        new_cabinet = CabinetORM(
            name=cabinet_name,
            table_link=google_sheets_url,
            user_id=user_id
        )
        session.add(new_cabinet)
        await session.commit()
    await message.answer("Кабинет успешно добавлен!")
    await state.set_state(SellerStates.waiting_for_tap_to_menu)
    logging.info(f"added {user_data["telegram_id"]} into 'users'")
    
    
@router.message(StateFilter(SellerStates.waiting_for_new_google_sheets_url))
async def handle_url(
    message: Message,
    state: FSMContext,
):
    google_sheets_url = message.text if message.text else "-"
    await state.update_data(
        google_sheets_url=google_sheets_url
    )
    await message.answer(f"Вот ваша ссылка на таблицу: {google_sheets_url}")
    await message.answer("Отправьте теперь название для вашего кабинета")
    await state.set_state(SellerStates.waiting_for_cabinet_name)
    
    
# catch upexpected text from seller
@router.message(StateFilter(SellerStates.waiting_for_tap_to_menu))
async def waiting_for_tap_to_menu(message: Message):
    await message.answer("Пожалуйста, выберите пункт в меню и продолжим.")
