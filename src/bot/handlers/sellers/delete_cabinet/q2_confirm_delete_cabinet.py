import datetime
import logging
from pathlib import Path
from aiogram import F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete, update

from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.sql import func
from src.db.models import CabinetORM, UserORM, ArticleORM
from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.core.config import constants, settings
from src.bot.keyboards.reply.menu import kb_menu

from .router import router

# Хэндлер запроса подтверждения
@router.callback_query(F.data.startswith("confirm_delete_"), StateFilter(SellerStates.waiting_for_delete_confirmation))
async def request_delete_confirmation(
    callback: CallbackQuery, 
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    
    # Извлекаем ID кабинета из callback_data
    cabinet_id_str = callback.data.split("_")[-1]
    cabinet_id = int(cabinet_id_str)
    
    # Сохраняем выбранный ID во временных данных FSM, чтобы использовать его позже
    await state.update_data(cabinet_to_delete_id=cabinet_id)

    # Создаем клавиатуру подтверждения
    confirmation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да, удалить ✅", callback_data=f"execute_delete_{cabinet_id}"),
            InlineKeyboardButton(text="Нет, отмена ❌", callback_data="cancel_deletion")
        ]
    ])

    # Получаем название кабинета из БД, чтобы вывести его в сообщении
    async with db_session_factory() as session:
        result = await session.execute(select(CabinetORM).where(CabinetORM.id == cabinet_id))
        cabinet = result.scalar_one_or_none()
        brand_name = cabinet.brand_name if cabinet else "Неизвестный кабинет"

        await callback.message.edit_text(
            f"Вы уверены, что хотите удалить кабинет *{brand_name}* и все связанные с ним артикулы?",
            parse_mode="Markdown",
            reply_markup=confirmation_keyboard
        )
    
    await callback.answer()

# Хэндлер отмены удаления
@router.callback_query(F.data == "cancel_deletion", StateFilter(SellerStates.waiting_for_delete_confirmation))
async def cancel_deletion(
    callback: CallbackQuery, 
    state: FSMContext
):
    await callback.message.edit_text("Удаление отменено.", reply_markup=None)
    await callback.message.answer(reply_markup=kb_menu) 
    await state.set_state(SellerStates.waiting_for_tap_to_menu)
    await callback.answer()

# Хэндлер выполнения удаления
@router.callback_query(F.data.startswith("execute_delete_"), StateFilter(SellerStates.waiting_for_delete_confirmation))
async def execute_deletion(
    callback: CallbackQuery, 
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    
    # Получаем ID кабинета, который ранее сохранили в FSM (или из callback_data, как здесь)
    cabinet_id_str = callback.data.split("_")[-1]
    cabinet_id = int(cabinet_id_str)

    async with db_session_factory() as session:
        # 1. Удаляем все артикулы, связанные с этим кабинетом
        # Используем sqlalchemy.delete для DML операций
        stmt_delete_articles = delete(ArticleORM).where(ArticleORM.cabinet_id == cabinet_id)
        await session.execute(stmt_delete_articles)

        # 2. Удаляем сам кабинет (или помечаем как удаленный, если используем soft-delete)
        # Если вы хотите физически удалить строку:
        # stmt_delete_cabinet = delete(CabinetORM).where(CabinetORM.id == cabinet_id)
        # await session.execute(stmt_delete_cabinet)
        
        # Если используете soft-delete (у вас в модели есть deleted_at):
        stmt_soft_delete = update(CabinetORM).where(CabinetORM.id == cabinet_id).values(deleted_at=func.now())
        await session.execute(stmt_soft_delete)

        # Коммитим изменения в БД
        await session.commit()


    await state.set_state(SellerStates.waiting_for_tap_to_menu)

    await callback.message.edit_text(
        f"Кабинет (ID: {cabinet_id}) и все его артикулы успешно удалены.", 
        reply_markup=None # Возвращаем основное меню
    )
    await callback.message.answer(reply_markup=kb_menu) 
    await callback.answer()