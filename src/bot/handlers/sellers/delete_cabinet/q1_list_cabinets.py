import logging
from pathlib import Path
from aiogram import F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.db.models import CabinetORM, UserORM
from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.core.config import constants, settings
from src.bot.keyboards.reply.menu import kb_menu

from .router import router

# SELLER_MENU_TEXT[1] == '❌Удалить кабинет'
@router.message(F.text == constants.SELLER_MENU_TEXT[1], StateFilter(SellerStates.waiting_for_tap_to_menu))
async def delete_cabinet(
    message: Message,
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    telegram_id = message.from_user.id


    async with db_session_factory() as session:
        user_result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            await message.answer("Ошибка: пользователь не найден в базе данных.")
            return

        user_id = user.id

        cabinets_result = await session.execute(
            select(CabinetORM).where(
                CabinetORM.user_id == user_id,
                CabinetORM.deleted_at.is_(None)
            )
        )
        cabinets = cabinets_result.scalars().all()

        if not cabinets:
            await message.answer(
                "У вас пока нет зарегистрированных кабинетов для удаления.",
                reply_markup=kb_menu
            )
            return

        buttons = []
        for cabinet in cabinets:
            button = InlineKeyboardButton(
                text=cabinet.brand_name,
                # Используем префикс 'confirm_delete_' для идентификации запроса на удаление
                callback_data=f"confirm_delete_{cabinet.id}" 
            )
            buttons.append([button]) 

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await message.answer(
            "Выберите кабинет для удаления:",
            reply_markup=keyboard
        )
        
        # Переводим пользователя в состояние ожидания выбора кабинета для удаления
        await state.set_state(SellerStates.waiting_for_delete_confirmation)
