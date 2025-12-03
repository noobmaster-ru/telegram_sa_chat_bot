import logging
from pathlib import Path
from aiogram import F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.db.models import UserORM, CabinetORM
from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.core.config import constants, settings
from src.bot.keyboards.reply.menu import kb_menu

from .router import router

# SELLER_MENU_TEXT[3] == '⬆️мой артикул'
@router.message(F.text == constants.SELLER_MENU_TEXT[3], StateFilter(SellerStates.waiting_for_tap_to_menu))
async def choose_cabinet(
    message: Message,
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    # 1. Получаем telegram_id текущего пользователя
    telegram_id = message.from_user.id
    
    async with db_session_factory() as session:
        # 2. Находим внутренний ID пользователя в БД
        user_result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
    
        if not user:
            logging.info(f" user {telegram_id} not find on db")
            await message.answer("Ошибка: пользователь не найден в базе данных.")
            return
        
        user_id = user.id
        
        # 3. Находим все кабинеты, принадлежащие этому пользователю
        cabinets_result = await session.execute(
            select(CabinetORM).where(
                CabinetORM.user_id == user_id,
                CabinetORM.deleted_at.is_(None) # Учитываем, что у вас есть deleted_at
            )
        )
        cabinets = cabinets_result.scalars().all()
        
        
        # 4. Формируем Inline-клавиатуру
        if not cabinets:
            await message.answer(
                "У вас пока нет зарегистрированных кабинетов.",
                reply_markup=kb_menu # Возвращаем основную клавиатуру меню
            )
            return

        # Создаем список кнопок
        buttons = []
        for cabinet in cabinets:
            # Для каждой кнопки используем brand_name в качестве текста 
            # и cabinet.id в качестве уникального callback_data
            button = InlineKeyboardButton(
                text=cabinet.brand_name,
                callback_data=f"select_cabinet_{cabinet.id}" 
                # Используйте префикс (например, "select_cabinet_") для обработки колбэка позже
            )
            buttons.append([button]) # Добавляем кнопку как отдельный ряд
        
        # Создаем объект разметки
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # 5. Отправляем сообщение с Inline-клавиатурой
        msg = await message.answer(
            "Выберите кабинет из списка ниже для добавления артикула:",
            reply_markup=keyboard
        )
        await state.update_data(
            message_id_to_delete=msg.message_id
        )
    
    