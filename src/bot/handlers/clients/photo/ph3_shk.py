import asyncio
import base64
import filetype
from typing import List, Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker
from pathlib import Path
from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.states.client import ClientStates
from src.bot.utils.get_reference_image import get_reference_image_data_url_cached
from src.bot.utils.last_activity import update_last_activity
from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass
from src.core.config import constants, settings
from src.db.models import CabinetORM

from .router import router


# ==== Получение фото от пользователя ==== 
@router.business_message(F.photo, StateFilter(ClientStates.waiting_for_photo_shk))
async def handle_photo_shk(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    redis: Redis,
    db_session_factory: async_sessionmaker,
    cabinet: CabinetORM,
    client_gpt_5: OpenAiRequestClass,
    album: Optional[List[Message]] = None
):
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    user_data = await state.get_data()
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    if album:    
        # Отправляем ТОЛЬКО ОДНО предупреждение 
        # (этот хэндлер вызовется только один раз для всего альбома благодаря middleware)
        msg = await message.answer(
            "Пожалуйста, отправьте *только одну* фотографию: фотографию *разрезанных этикеток* товара",
            parse_mode="MarkdownV2"
        )
        await update_last_activity(state, msg)
        # Остаемся в том же состоянии, чтобы он отправил одну фотографию
        await state.set_state(ClientStates.waiting_for_photo_shk)
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

    # # обновляем время последнего сообщения юзера
    # await spreadsheet.update_buyer_last_time_message(
    #     telegram_id=telegram_id,
    #     is_tap_to_keyboard=False
    # )
    

    # 4. Берём эталон из кэша / TG
    ref_image_url = await get_reference_image_data_url_cached(
        db_session_factory=db_session_factory,
        redis=redis,
        cabinet_id=cabinet.id,
        nm_id=nm_id,
        seller_bot_token=settings.SELLERS_BOT_TOKEN,
    )
    
    # отправляем в OpenAI для классификации
    model_response = await client_gpt_5.classify_photo_shk(
        ref_image_url=ref_image_url,
        user_image_url=user_image_url,
        nm_id=nm_id,
        nm_id_name=nm_id_name
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
        await message.answer(
            text=f"✅ Фото разрезанных этикеток принято\\!",
            parse_mode="MarkdownV2"
        )
        await message.answer("☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо!")
        msg = await message.answer(
            "Отправьте теперь нам, пожалуйста, свой номер телефона в формате:\n\n*\\+7910XXXXXXX*\n\nСпасибо",
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_requisites)
        await update_last_activity(state, msg)
    else:
        await state.set_state(ClientStates.waiting_for_photo_shk)
        msg = await message.answer("❌ Фото разрезанных штрихкодов не принято. Пожалуйста, разрежьте этикетки и пришлите фото ещё раз☺️")
        await update_last_activity(state, msg)
