import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import  Message, InlineKeyboardMarkup, InlineKeyboardButton

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.reply import kb_menu

from src.infrastructure.db.models import CabinetORM, UserORM
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

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

        text = "Ошибка: пользователь не найден в базе данных."
        if not user:
            await message.answer(
                StringConverter.escape_markdown_v2(text),
                parse_mode="MarkdownV2"
            )
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
            text = "У вас пока нет зарегистрированных кабинетов для удаления."
            await message.answer(
                text=StringConverter.escape_markdown_v2(text),
                reply_markup=kb_menu,
                parse_mode="MarkdownV2"
            )
            return

        buttons = []
        for cabinet in cabinets:
            button = InlineKeyboardButton(
                text=cabinet.organization_name,
                # Используем префикс 'confirm_delete_' для идентификации запроса на удаление
                callback_data=f"confirm_delete_{cabinet.id}" 
            )
            buttons.append([button]) 

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = "Выберите кабинет для удаления:"
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            reply_markup=keyboard,
            parse_mode="MarkdownV2"
        )
        
        # Переводим пользователя в состояние ожидания выбора кабинета для удаления
        await state.set_state(SellerStates.waiting_for_delete_confirmation)
