import logging
from redis.asyncio import Redis

from aiogram import F
from aiogram.filters import StateFilter, or_f
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.app.bot.filters.image_document import ImageDocument
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.keyboards.reply import kb_buy_leads
from src.app.bot.utils.get_reference_image import get_reference_image_data_url_cached
from src.app.bot.states.seller import SellerStates
from src.infrastructure.db.models import (
    ArticleORM, 
    CabinetORM
)
from src.tools.string_converter_class import StringConverter
from src.core.config import settings, constants

from .router import router


@router.message(F.text, StateFilter(SellerStates.waiting_for_nm_id))
async def handle_nm_id(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    seller_data = await state.get_data()
    organization_name = seller_data.get("organization_name", "-")

    if not text.isdigit():
        text = "Введите артикул числом, *только цифры*"
        return await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2",
        )

    nm_id = int(text)
    await state.update_data(nm_id=nm_id)

    text = (
        f"Магазин: *{organization_name}*\n"
        f"Артикул: *{nm_id}*\n\n"
        f"Введите название товара (*ОЧЕНЬ ВАЖНО УКАЗАТЬ ИМЕННО ТАК, КАК ТОВАР НАЗЫВАЕТСЯ НА ВБ - AI БУДЕТ СРАВНИВАТЬ НАЗВАНИЕ ТОВАРА НА СКРИНШОТАХ*):"
    )
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
    )
    await state.set_state(SellerStates.waiting_for_nm_id_name)


@router.message(F.text, StateFilter(SellerStates.waiting_for_nm_id_name))
async def handle_nm_id_amount(message: Message, state: FSMContext):
    nm_id_name = (message.text or "").capitalize()
    seller_data = await state.get_data()
    organization_name = seller_data.get("organization_name", "-")
    nm_id = seller_data.get("nm_id")


    await state.update_data(nm_id_name=nm_id_name)

    text = (
        f"Магазин: *{organization_name}*\n"
        f"Артикул: *{nm_id}*\n"
        f"Название товара: *{nm_id_name}*\n\n"
        f"Теперь отправьте *первое* фото товара в карточке."
    )
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
    )
    await state.set_state(SellerStates.waiting_for_nm_id_photo)


@router.message(
    or_f(F.photo, ImageDocument()), 
    StateFilter(SellerStates.waiting_for_nm_id_photo)
)
async def handle_nm_id_photo(
    message: Message,
    state: FSMContext,
):
    seller_data = await state.get_data()

    # 1. Проверка на альбом
    if message.media_group_id is not None:
        last_media_group = seller_data.get("last_media_group_id")

        if last_media_group == message.media_group_id:
            return

        await state.update_data(last_media_group_id=message.media_group_id)
        text = "Пожалуйста, отправьте только одну фотографию: первую фотографию артикула."
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    nm_id = seller_data["nm_id"]
    nm_id_name = seller_data["nm_id_name"]
    organization_name = seller_data.get("organization_name", "-")

    # 2. Определяем file_id (фото или документ)
    photo_file_id = None
    is_photo = False
    
    if message.photo:
        photo_file_id = message.photo[-1].file_id   # лучшее качество
        is_photo = True
    elif message.document:
        photo_file_id = message.document.file_id
        is_photo = False
    else:
        text = "Не удалось найти изображение в сообщении. Пришлите, пожалуйста, фото ещё раз."
        msg = await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_nm_id_photo)
        return
    
    # 3. Сохраняем file_id как есть — не важно, photo это или document
    await state.update_data(nm_id_photo_file_id=photo_file_id)
    
    caption = (
        f"Магазин: *{organization_name}*\n"
        f"Артикул: *{nm_id}*\n"
        f"Название товара: *{nm_id_name}*\n\n\n"
        f"Данные заполнены верно?"
    )
    # 4. Отправляем превью в зависимости от типа
    if is_photo:
        msg = await message.answer_photo(
            photo=photo_file_id,
            caption=caption,
            reply_markup=get_yes_no_keyboard(
                callback_prefix="data_verify",
                statement="верно",
            ),
            parse_mode="MarkdownV2",
        )
    else:
        # документ (изображение без сжатия) — отправляем как документ
        msg = await message.answer_document(
            document=photo_file_id,
            caption=caption,
            reply_markup=get_yes_no_keyboard(
                callback_prefix="data_verify",
                statement="верно",
            ),
            parse_mode="MarkdownV2",
        )  

    await state.update_data(
        message_id_to_delete=msg.message_id,
    )


@router.callback_query(F.data.startswith("data_verify"))
async def write_data_into_db(
    callback: CallbackQuery,
    state: FSMContext,
    db_session_factory: async_sessionmaker,
    redis: Redis,
):
    await callback.answer()
    seller_data = await state.get_data()
    message_id_to_delete = seller_data["message_id_to_delete"]

    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=message_id_to_delete,
    )
    del seller_data["message_id_to_delete"]
    await state.set_data(seller_data)

    if callback.data == "data_verify_yes":
        nm_id = seller_data["nm_id"]
        nm_id_name = seller_data["nm_id_name"]
        cabinet_id = seller_data["cabinet_id"]  # установлен в q3_service_account_access
        file_id = seller_data["nm_id_photo_file_id"]
        organization_name = seller_data.get("organization_name", "-")


        async with db_session_factory() as session:
            # 1. Загружаем кабинет и обновляем nm_id_name
            cabinet = await session.get(CabinetORM, cabinet_id)
            if cabinet is None:
                # На всякий случай защита — если что-то пошло не так с FSM
                text = "Не удалось найти кабинет в базе. Попробуйте начать заново с /start."
                await callback.message.answer(
                    text=StringConverter.escape_markdown_v2(text),
                    parse_mode="MarkdownV2"
                )
                return

            cabinet.nm_id_name = nm_id_name  # тут мы перезатираем заглушку
            
            # 2. Сохраняем артикул в БД
            new_article = ArticleORM(
                cabinet_id=cabinet_id,
                article=nm_id,
                nm_id_name=nm_id_name,
                photo_file_id=file_id,
            )
            session.add(new_article)
            await session.commit()
            await session.refresh(new_article)
            await session.refresh(cabinet)
        
        # 2. Сразу прогреваем кэш эталонного изображения в Redis
        # (чтобы clients_bot больше не ходил в Telegram за этой фоткой)
        await get_reference_image_data_url_cached(
            db_session_factory=db_session_factory,
            redis=redis,
            cabinet_id=cabinet_id,
            nm_id=nm_id,
            seller_bot_token=settings.SELLERS_BOT_TOKEN,
        )


        text = (
            f"Магазин: *{organization_name}*\n"
            f"Артикул: *{nm_id}*\n"
            f"Название товара: *{nm_id_name}*\n\n\n"
            f"Успешно добавлен🎉"
        )
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2",
        )
        
        text=f"Теперь необходимо купить лиды на кабинет, нажмите на клавиатуре {constants.SELLER_MENU_TEXT[1]}"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            reply_markup=kb_buy_leads,
            parse_mode="MarkdownV2",
        )
        await state.set_state(SellerStates.waiting_for_leads)
    else:
        text = "Хорошо, давайте добавим артикул заново. Отправьте артикул товара на ВБ (число)."
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_nm_id)


@router.message(StateFilter(SellerStates.waiting_for_nm_id_photo))
async def not_photo_warning(message: Message):
    text = "Пожалуйста, отправьте *одно* фото товара."
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )