import asyncio
import base64
import filetype
from typing import List, Optional


from sqlalchemy.ext.asyncio import async_sessionmaker
from redis.asyncio import Redis
from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.filters.image_document import ImageDocument
from src.bot.states.client import ClientStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.utils.last_activity import update_last_activity
from src.bot.utils.get_reference_image import get_reference_image_data_url_cached

from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass

from src.core.config import constants, settings
from src.db.models import CabinetORM

from .router import router


# ==== Получение скрина заказа от пользователя ==== 
@router.business_message(
    or_f(F.photo, ImageDocument()), 
    StateFilter(ClientStates.waiting_for_photo_order)
)
async def handle_photo_order(
    message: Message,
    state: FSMContext,
    redis: Redis,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
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
    
    # 1. Проверяем медиагруппу
    if album:    
        msg = await message.answer(
            "Пожалуйста, отправьте *только один* скриншот: скриншот *ЗАКАЗА* товара",
            parse_mode="MarkdownV2"
        )
        await update_last_activity(state, msg)
        await state.set_state(ClientStates.waiting_for_photo_order)
        return


    # === 2. Извлекаем данные из FSM ===
    telegram_id = message.from_user.id
    nm_id = user_data.get("nm_id")
    nm_id_name = user_data.get("nm_id_name")
    

    # === 3. Получаем фото юзера (как photo ИЛИ как document) ===
    # Если отправлено как обычное фото
    if message.photo:
        tg_file_id = message.photo[-1].file_id   # лучшее качество
    # Если отправлено как файл "без сжатия" (image/*)
    elif message.document:
        tg_file_id = message.document.file_id
    else:
        # Теоретически сюда не попадём из-за фильтра, но на всякий случай
        msg = await message.answer(
            "Не удалось найти изображение в сообщении. Пришлите, пожалуйста, скриншот ещё раз."
        )
        await update_last_activity(state, msg)
        await state.set_state(ClientStates.waiting_for_photo_order)
        return
    

    file = await message.bot.get_file(tg_file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    user_bytes = file_bytes.read()
    
    # 🔹 Конвертируем байты в base64-строку
    base64_image_user = base64.b64encode(user_bytes).decode("utf-8")
    
    # Определяем расширение по содержимому, а не по имени
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


    if ref_image_url is None:
        await message.answer(
            "Не удалось найти эталонное изображение для этого артикула. "
            "Попросите менеджера проверить настройки."
        )
        return
    
    # отправляем в OpenAI для классификации
    model_response = await client_gpt_5.classify_photo_order(
        ref_image_url=ref_image_url,
        user_image_url=user_image_url,
        nm_id=nm_id,
        nm_id_name=nm_id_name
    )

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name="photo_order",
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
        await state.update_data(photo_type="feedback")
        await message.answer(
            text=f"✅ Скриншот заказа принят\\!",
            parse_mode="MarkdownV2"
        )
        # записали фотку заказа - теперь идем дальше по сценарию - спрашиваем получили ли заказ
        msg = await message.answer(
            f"📬 Когда получите {nm_id_name}, нажмите на кнопку Да, получил ниже", 
            reply_markup=get_yes_no_keyboard("receive", "получил(а)")
        )
        await state.set_state(ClientStates.waiting_for_order_receive)
        await update_last_activity(state, msg)
    else:
        await state.set_state(ClientStates.waiting_for_photo_order)
        msg = await message.answer("❌ Фото заказа не принято. Попробуйте прислать корректное фото заказа.")
        await update_last_activity(state, msg)
