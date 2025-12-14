import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.reply import kb_menu
from src.infrastructure.db.models import CabinetORM, UserORM, ArticleORM, CashbackTableORM
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router


# SELLER_MENU_TEXT[2] == 'ℹ️Мой кабинет'
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
            text = "Пользователь не найден. Нажмите /start"
            await message.answer(
                text=StringConverter.escape_markdown_v2(text),
                parse_mode="MarkdownV2"
            )
            return

        # Загружаем кабинеты юзера
        result = await session.execute(
            select(CabinetORM)
            .where(CabinetORM.user_id == user.id)
            .order_by(CabinetORM.created_at)
        )
        cabinets = result.scalars().all()

        if not cabinets:
            text = "У вас пока нет подключённых кабинетов."
            await message.answer(
                text=StringConverter.escape_markdown_v2(text), 
                reply_markup=kb_menu,
                parse_mode="MarkdownV2"
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
                        f"{i}. google_sheets_id: `{tbl.table_id}` , статус: *{tbl.status.value}*"
                    )
                tables_text = "*Таблица кэшбека:*\n" + "\n".join(table_lines) + "\n\n"
            else:
                tables_text = "Таблица кэшбека пока не подключена.\n\n"

            # Артикулы
            if articles:
                lines = []
                for i, art in enumerate(articles, start=1):
                    lines.append(f"{i}. {art.article} — {art.nm_id_name}")
                articles_text = "*Артикул:*\n" + "\n".join(lines)
            else:
                articles_text = "Артикула пока нет."


            # Сначала отправляем текст
            text_message = header + tables_text + articles_text
            await message.answer(
                text=StringConverter.escape_markdown_v2(text_message),
                parse_mode="MarkdownV2",
            )

            # Затем отправляем фото каждого артикула ОДНИМ сообщением
            photos: list[InputMediaPhoto] = []

            for i, art in enumerate(articles, start=1):
                if art.photo_file_id:
                    if not photos:
                        # Первая фотография — с подписью
                        caption = (
                            f"Фото артикула {', '.join(article_numbers)}"
                            if article_numbers
                            else "Фото артикула"
                        )
                        caption_safe = StringConverter.escape_markdown_v2(caption)
                        photos.append(
                            InputMediaPhoto(
                                media=art.photo_file_id,
                                caption=caption_safe,
                                parse_mode="MarkdownV2"
                            )
                        )
                    else:
                        # Остальные — без подписи
                        photos.append(
                            InputMediaPhoto(
                                media=art.photo_file_id,
                                parse_mode="MarkdownV2"
                            )
                        )

            # Отправляем медиагруппу, если есть фото
            if photos:
                await message.bot.send_media_group(
                    chat_id=message.chat.id,
                    media=photos,
                )

    # Возвращаем меню
    text = "Вот ваша таблица кэшбека, артикул и название ☝️"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=kb_menu,
        parse_mode="MarkdownV2"
    )