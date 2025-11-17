import asyncio
import base64
import filetype
from pathlib import Path
from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.states.user_flow import UserFlow
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.google_sheets_class import GoogleSheetClass
from src.bot.utils.last_activity import update_last_activity


from .router import router


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# ==== Получение фото от пользователя уже после скрина заказа/отзыва/шк ==== 
@router.business_message(F.photo, StateFilter(UserFlow.waiting_for_requisites, UserFlow.continue_dialog))
async def handle_photo_other_type(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass
):
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )

    # === 2. Извлекаем данные из FSM ===
    telegram_id = message.from_user.id

    # обновляем время последнего сообщения юзера
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    
    # photo_type == "other_type" ,юзер тупой и продолжает отправлять ненужные фотографии
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = message.business_connection_id
    )
    await asyncio.sleep(3)
    current_state = await state.get_state() 
    if current_state == UserFlow.waiting_for_requisites:
        msg = await message.answer(
            "☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, теперь отправьте нам свои реквизиты в формате:\nНомер карты в формате: AAAA BBBB CCCC DDDD\n *ИЛИ* \nНомер телефона: 8910XXXXXXX",
            parse_mode="MarkdownV2"
        )
        await update_last_activity(state, msg)
    elif current_state == UserFlow.continue_dialog:
        await message.answer("Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, напишите ваш вопрос текстом.")