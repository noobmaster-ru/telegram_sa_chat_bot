import asyncio
import base64
import filetype
from typing import List, Optional

from aiogram import F
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.states.client import ClientStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.utils.get_reference_image import get_reference_image_data_url_cached
from src.db.models import CabinetORM

from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass
from src.bot.utils.last_activity import update_last_activity
from src.core.config import constants, settings

from .router import router

# ==== Получение скрина отзыва от пользователя ==== 
@router.business_message(F.photo, StateFilter(ClientStates.waiting_for_photo_feedback))
async def handle_photo_feedback(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    redis: Redis,
    db_session_factory: async_sessionmaker,
    cabinet: CabinetORM,
    album: Optional[List[Message]] = None
):
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    user_data = await state.get_data()
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    # Middleware соберет все сообщения в album
    # Если 'album' существует, значит, юзер отправил медиагруппу
    if album:    
        # Отправляем ТОЛЬКО ОДНО предупреждение 
        # (этот хэндлер вызовется только один раз для всего альбома благодаря middleware)
        msg = await message.answer(
            "Пожалуйста, отправьте *только один* скриншот: скриншот *ОТЗЫВА* товара",
            parse_mode="MarkdownV2"
        )
        await update_last_activity(state, msg)
        # Остаемся в том же состоянии, чтобы он отправил одну фотографию
        await state.set_state(ClientStates.waiting_for_photo_feedback)
        return


    # === 2. Извлекаем данные из FSM ===
    telegram_id = message.from_user.id
    nm_id = user_data.get("nm_id")
    nm_id_name = user_data.get("nm_id_name")
    
    # === 3. Получаем фото ===
    photo = message.photo[-1]  # лучшее качество
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    user_bytes = file_bytes.read()
    # 🔹 Конвертируем байты в base64-строку
    base64_image_user = base64.b64encode(user_bytes).decode("utf-8")
    reference_image_extension = filetype.guess(user_bytes).extension
    user_image_url  = f"data:image/{reference_image_extension};base64,{base64_image_user}"

    
    # 4. Берём эталон из кэша / TG
    ref_image_url = await get_reference_image_data_url_cached(
        db_session_factory=db_session_factory,
        redis=redis,
        cabinet_id=cabinet.id,
        nm_id=nm_id,
        seller_bot_token=settings.SELLERS_BOT_TOKEN,
    )
    
    
    # отправляем в OpenAI для классификации
    model_response = await client_gpt_5.classify_photo_feedback(
        ref_image_url=ref_image_url,
        user_image_url=user_image_url,
        nm_id=nm_id,
        nm_id_name=nm_id_name
    )

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name="photo_feedback",
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
        # теперь ждём скрин отзыва
        await state.update_data(photo_type="shk")
        # отвечаем пользователю
        await message.answer(
            text=f"✅ Скриншот отзыва принят\\!",
            parse_mode="MarkdownV2"
        )
        #  Следующий вопрос - разрезали ли ШК
        msg = await message.answer(
            f"✂️ Этикетки разрезали на {nm_id_name}?", 
            reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
        )
        await state.set_state(ClientStates.waiting_for_shk)
        await update_last_activity(state, msg)
    else:
        await state.set_state(ClientStates.waiting_for_photo_feedback)
        msg = await message.answer("❌ Фото отзыва не принято. Попробуйте прислать корректное фото отзыва.")
        await update_last_activity(state, msg)