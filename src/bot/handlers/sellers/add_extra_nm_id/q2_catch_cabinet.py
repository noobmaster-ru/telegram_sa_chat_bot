# Нужно импортировать MagicFilter, если используете F.callback_data.startswith
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
from src.services.string_converter_class import StringConverter
from src.core.config import constants, settings
from src.bot.keyboards.reply.menu import kb_menu

from .router import router

@router.callback_query(F.data.startswith("select_cabinet_"))
async def process_cabinet_selection(
    callback: CallbackQuery, 
    db_session_factory: async_sessionmaker, 
    state: FSMContext
):
    await callback.answer()
    seller_data = await state.get_data() 
    message_id_to_delete = seller_data["message_id_to_delete"]
    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=message_id_to_delete
    )
    del seller_data['message_id_to_delete']
    await state.set_data(seller_data)
    # 1. Извлекаем ID кабинета из callback_data
    cabinet_id_str = callback.data.split("_")[-1]
    cabinet_id = int(cabinet_id_str)
    
    async with db_session_factory() as session:
        # 2. Получаем объект кабинета из БД, чтобы узнать его название
        cabinet_result = await session.execute(
            select(CabinetORM).where(CabinetORM.id == cabinet_id)
        )
        selected_cabinet = cabinet_result.scalar_one_or_none()
        
        if not selected_cabinet:
            logging.info(" error: cabinet not found")
            await callback.answer("Ошибка: Кабинет не найден.", show_alert=True)
            return
        # 3. Сохраняем ID кабинета в FSM для дальнейшего использования
        await state.update_data(current_cabinet_id=cabinet_id)

        # 4. Отправляем пользователю подтверждение с НАЗВАНИЕМ
        # show_alert=False (по умолчанию) показывает всплывающее уведомление снизу экрана
        await callback.message.answer(
            text=f"Выбран кабинет: {selected_cabinet.brand_name}\n\nВведите новый артикул:",
            reply_markup=ReplyKeyboardRemove() 
        )

        
        # 5. Редактируем предыдущее сообщение, чтобы убрать inline-кнопки выбора
        # Например, заменяем кнопки на меню действий внутри кабинета
        # await callback.message.edit_text("Меню кабинета:")
        # await callback.message.edit_reply_markup(reply_markup=kb_cabinet_menu)
        
        # wait for a new nm_id
        await state.set_state(SellerStates.waiting_for_nm_id)
