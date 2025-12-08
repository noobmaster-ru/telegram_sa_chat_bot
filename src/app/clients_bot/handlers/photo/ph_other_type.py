import asyncio
from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.app.bot.states.client import ClientStates
from src.app.bot.utils.last_activity import update_last_activity
from src.app.bot.filters.image_document import ImageDocument
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

# ==== Получение фото от пользователя уже после скрина заказа/отзыва/шк ==== 
@router.business_message(
    or_f(F.photo, ImageDocument()), 
    StateFilter(ClientStates.waiting_for_requisites, ClientStates.continue_dialog)
)
async def handle_photo_other_type(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass
):
    # === 2. Извлекаем данные из FSM ===
    current_state = await state.get_state() 
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    telegram_id = message.from_user.id
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )

    # # обновляем время последнего сообщения юзера
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        text=text
    )
    

    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER) 
    if current_state == ClientStates.waiting_for_requisites:
        text = "☺️ Вы прислали все фотографии, которые были нам нужны, Спасибо! Пожалуйста, теперь отправьте нам свои реквизиты в формате:\nНомер телефона: *+7910XXXXXXX*",
        msg = await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_requisites)
        await update_last_activity(state, msg)
   
    elif current_state == ClientStates.continue_dialog:
        text = "Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, напишите ваш вопрос текстом."
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.continue_dialog)