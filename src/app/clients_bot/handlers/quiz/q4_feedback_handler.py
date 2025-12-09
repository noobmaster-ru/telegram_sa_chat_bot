import logging
from aiogram import F, types, Bot
from aiogram.enums import ChatAction
from aiogram.types import  CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage
from aiogram.filters import StateFilter

from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.states.client import ClientStates
from src.app.bot.utils.last_activity import update_last_activity
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.infrastructure.apis.open_ai_requests_class import OpenAiRequestClass
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

# ------ 5. catch all text from user in state "waiting_for_feedback" and send it to gpt 
@router.business_message(StateFilter(ClientStates.waiting_for_feedback))
async def handle_unexpected_text_waiting_for_feedback_done(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext,
    bot: Bot
):
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    telegram_id = message.from_user.id
    text = message.text
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    client_data = await state.get_data()
    instruction = client_data.get("instruction")
    
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        text=text
    )
    
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_receive_product_and_before_feedback_check_point(
        new_prompt=text,
        instruction=instruction
    )
    await state.set_state(ClientStates.waiting_for_feedback)
    msg = await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("feedback", "оставил(а) отзыв")
    )
    await update_last_activity(state, msg)

# ------ 5. wait until user tap to button "Yes, made feedback" and go to the state "waiting_for_photo_feedback"
@router.callback_query(StateFilter(ClientStates.waiting_for_feedback), F.data.startswith("feedback_"))
async def handle_feedback_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    state: FSMContext,
):
    await callback.answer()
    """Обработка нажатия кнопок Да/Нет"""
    telegram_id = callback.from_user.id
    data = callback.data
    business_connection_id = callback.message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"
    
    client_data = await state.get_data()
    nm_id_name = client_data.get("nm_id_name")
    
    messages_ids_to_delete = client_data["last_messages_ids"]
    if messages_ids_to_delete:
        try:
            await callback.bot.delete_business_messages(
                business_connection_id=business_connection_id,
                message_ids=messages_ids_to_delete
            )
            await state.update_data(last_messages_ids=[])
        except: 
            await state.update_data(last_messages_ids=[])
            logging.info("cant delete message in q4")
    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )
    msg = None
    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        text = f"Когда оставите отзыв на товар {nm_id_name}, нажмите, пожалуйста, на кнопку ниже"
        msg = await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text), 
            reply_markup=get_yes_no_keyboard("feedback", "оставил(а)"),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_feedback)
        await update_last_activity(state, msg)
        return
    
    # дальше переходим в состояние waiting_for_photo_feedback - ждем фотки отзыва от юзера
    text = f"Отправьте, пожалуйста, скриншот отзыва на 5 звёзд"
    msg = await callback.message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )
    await state.set_state(ClientStates.waiting_for_photo_feedback)
    await update_last_activity(state, msg)
   