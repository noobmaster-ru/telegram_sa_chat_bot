import asyncio
import base64
import filetype
from typing import List, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.app.bot.filters.image_document import ImageDocument
from src.app.bot.states.client import ClientStates

from src.app.bot.utils.last_activity import update_last_activity
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.infrastructure.apis.open_ai_requests_class import OpenAiRequestClass
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

# ==== Получение фото от пользователя ==== 
@router.business_message(
    or_f(F.photo, ImageDocument()),
    StateFilter(ClientStates.waiting_for_photo_shk)
)
async def handle_photo_shk(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    album: Optional[List[Message]] = None
):
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    
    # 1. Проверяем медиагруппу
    if album:  
        text =  "Пожалуйста, отправьте *только одну* фотографию: фотографию *разрезанных этикеток* товара" 
        msg = await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await update_last_activity(state, msg)
        await state.set_state(ClientStates.waiting_for_photo_shk)
        return


    # === 2. Извлекаем данные из FSM ===
    telegram_id = message.from_user.id

    # === 3. Получаем фото юзера (как photo ИЛИ как document) ===
    # Если отправлено как обычное фото
    if message.photo:
        tg_file_id = message.photo[-1].file_id   # лучшее качество
    # Если отправлено как файл "без сжатия" (image/*)
    elif message.document:
        tg_file_id = message.document.file_id
    else:
        # Теоретически сюда не попадём из-за фильтра, но на всякий случай
        text = "Не удалось найти изображение в сообщении. Пришлите, пожалуйста, скриншот ещё раз."
        msg = await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await update_last_activity(state, msg)
        await state.set_state(ClientStates.waiting_for_photo_shk)
        return
    
    file = await message.bot.get_file(tg_file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    user_bytes = file_bytes.read()
    
    # 🔹 Конвертируем байты в base64-строку
    base64_image_user = base64.b64encode(user_bytes).decode("utf-8")
    
    # Определяем расширение по содержимому, а не по имени
    reference_image_extension = filetype.guess(user_bytes).extension
    user_image_url  = f"data:image/{reference_image_extension};base64,{base64_image_user}"

    
    # отправляем в OpenAI для классификации
    model_response = await client_gpt_5.classify_photo_shk(
        user_image_url=user_image_url
    )

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name="photo_shk",
        value=model_response,
        is_tap_to_keyboard=False
    )
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = message.business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    
    if model_response == "Да":
        # получили все фотки: заказ, отзыв, ШК
        await state.update_data(photo_type="other_type")
        # отвечаем пользователю
        text = f"✅ Фото разрезанных этикеток принято!"
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        text = "☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо!"
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        text = "Отправьте теперь нам, пожалуйста, свой номер телефона в формате:\n\n*+7910XXXXXXX*\n\nСпасибо"
        msg = await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_requisites)
        await update_last_activity(state, msg)
    else:
        await state.set_state(ClientStates.waiting_for_photo_shk)
        text = "❌ Фото разрезанных штрихкодов не принято. Пожалуйста, разрежьте этикетки и пришлите фото ещё раз☺️"
        msg = await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await update_last_activity(state, msg)
