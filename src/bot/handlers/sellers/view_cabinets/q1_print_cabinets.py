import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from src.db.models import CabinetORM, UserORM, ArticleORM, CashbackTableORM
from src.bot.states.seller import SellerStates
from src.bot.keyboards.reply.menu import kb_menu
from src.tools.string_converter_class import StringConverter
from src.core.config import constants

from .router import router


# SELLER_MENU_TEXT[2] == 'ℹ️Посмотреть кабинеты'
@router.message(
    F.text == constants.SELLER_MENU_TEXT[2],
    StateFilter(SellerStates.waiting_for_tap_to_menu),
)
async def view_cabinets(
    message: Message,
    db_session_factory: async_sessionmaker,
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
            await message.answer(
                "У вас пока нет подключённых кабинетов.", reply_markup=kb_menu
            )
            return

        # Для каждого кабинета — отдельное сообщение
        for cabinet in cabinets:
            # Подтягиваем таблицы кэшбека этого кабинета
            result = await session.execute(
                select(CashbackTableORM)
                .where(CashbackTableORM.cabinet_id == cabinet.id)
                .order_by(CashbackTableORM.created_at)
            )
            cashback_tables = result.scalars().all()

            # Подтягиваем артикулы кабинета
            result = await session.execute(
                select(ArticleORM)
                .where(ArticleORM.cabinet_id == cabinet.id)
                .order_by(ArticleORM.created_at)
            )
            articles = result.scalars().all()
            article_numbers = [str(art.article) for art in articles]

            # --- Формируем текстовую часть ---

            # Организация
            header = f"*Магазин:* {cabinet.organization_name}\n"

            # Таблицы кэшбека
            if cashback_tables:
                table_lines = []
                for i, tbl in enumerate(cashback_tables, start=1):
                    # показываем table_id и статус
                    table_lines.append(
                        f"{i}. table_id: `{tbl.table_id}` , статус: *{tbl.status.value}*"
                    )
                tables_text = "*Таблицы кэшбека:*\n" + "\n".join(table_lines) + "\n\n"
            else:
                tables_text = "Таблицы кэшбека пока не подключены.\n\n"

            # Артикулы
            if articles:
                lines = []
                for i, art in enumerate(articles, start=1):
                    lines.append(f"{i}. {art.article} — {art.nm_id_name}")
                articles_text = "*Артикулы:*\n" + "\n".join(lines)
            else:
                articles_text = "Артикулов пока нет."

            text_message = header + tables_text + articles_text
            text_markdown2 = StringConverter.escape_markdown_v2(text_message)

            # Сначала отправляем текст
            await message.answer(
                text_markdown2,
                parse_mode="MarkdownV2",
            )

            # Затем отправляем фото каждого артикула ОДНИМ сообщением
            photos: list[InputMediaPhoto] = []

            for i, art in enumerate(articles, start=1):
                if art.photo_file_id:
                    if not photos:
                        # Первая фотография — с подписью
                        caption = (
                            f"Фото артикулов {', '.join(article_numbers)}"
                            if article_numbers
                            else "Фото артикулов"
                        )
                        caption_safe = StringConverter.escape_markdown_v2(caption)
                        photos.append(
                            InputMediaPhoto(
                                media=art.photo_file_id,
                                caption=caption_safe,
                            )
                        )
                    else:
                        # Остальные — без подписи
                        photos.append(
                            InputMediaPhoto(
                                media=art.photo_file_id,
                            )
                        )

            # Отправляем медиагруппу, если есть фото
            if photos:
                await message.bot.send_media_group(
                    chat_id=message.chat.id,
                    media=photos,
                )

    # Возвращаем меню
    await message.answer(
        "☝️Вот ваши кабинеты, таблицы кэшбека, артикулы и их названия",
        reply_markup=kb_menu,
    )