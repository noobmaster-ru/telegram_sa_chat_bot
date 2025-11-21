import logging
from pathlib import Path
from aiogram import F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery

from aiogram.types import InputMediaPhoto
from src.db.models import CabinetORM, UserORM, ArticleORM
from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.keyboards.reply.menu import kb_menu
from src.services.string_converter_class import StringConverter
from src.core.config import constants, settings

from .router import router

# SELLER_MENU_TEXT[2] == 'ℹ️Посмотреть кабинеты'
@router.message(F.text == constants.SELLER_MENU_TEXT[2], StateFilter(SellerStates.waiting_for_tap_to_menu))
async def view_cabinets(
    message: Message,
    db_session_factory: async_sessionmaker
):
    telegram_id = message.from_user.id

    async with db_session_factory() as session:
        # Находим юзера
        result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            await message.answer("Пользователь не найден. Нажмите /start")
            return
        
        # Загружаем кабинеты юзера
        result = await session.execute(
            select(CabinetORM)
            .where(CabinetORM.user_id == user.id)
            .order_by(CabinetORM.created_at)
        )
        cabinets = result.scalars().all()

        if not cabinets:
            await message.answer("У вас пока нет подключённых кабинетов.", reply_markup=kb_menu)
            return

        # Для каждого кабинета — отдельное сообщение
        for cabinet in cabinets:

            # Подтягиваем артикулы кабинета
            result = await session.execute(
                select(ArticleORM)
                .where(ArticleORM.cabinet_id == cabinet.id)
                .order_by(ArticleORM.created_at)
            )
            articles = result.scalars().all()
            article_numbers = [str(art.article) for art in articles]
            # Формируем текстовую часть
            header = (
                f"*Бренд:* {cabinet.brand_name}\n"
                f"*Таблица:* {cabinet.table_link}\n\n"
            )

            if articles:
                lines = []
                for i, art in enumerate(articles, start=1):
                    lines.append(f"{i}. {art.article} — {art.giveaways} раздач")
                articles_text = "\n".join(lines)
            else:
                articles_text = "Артикулов пока нет."

            text_message = header + articles_text
            text_markdown2 = StringConverter.escape_markdown_v2(text_message)
           
            # Сначала отправляем текст
            await message.answer(
                text_markdown2,
                parse_mode="MarkdownV2"
            )

            # Затем отправляем фото каждого артикула ОДНИМ сообщением
            photos = []

            for i, art in enumerate(articles, start=1):
                if art.photo_file_id:
                    if not photos:
                        # Первая фотография — с подписью
                        caption = f"Фото артикулов {', '.join(article_numbers)}"
                        caption_safe = StringConverter.escape_markdown_v2(caption)
                        photos.append(
                            InputMediaPhoto(
                                media=art.photo_file_id,
                                caption=caption_safe
                            )
                        )
                    else:
                        # Остальные — без подписи
                        photos.append(
                            InputMediaPhoto(
                                media=art.photo_file_id
                            )
                        )

            # Отправляем медиагруппу, если есть фото
            if photos:
                await message.bot.send_media_group(
                    chat_id=message.chat.id,
                    media=photos
                )

    # Возвращаем меню
    await message.answer(
        "☝️Вот ваши кабинеты, артикулы в них и количество раздач", 
        reply_markup=kb_menu
    )