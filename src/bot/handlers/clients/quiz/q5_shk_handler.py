import logging
from aiogram import F, Bot, types
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage
from aiogram.types import  CallbackQuery


from src.bot.states.client import ClientStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass
from src.bot.utils.last_activity import update_last_activity
from src.core.config import constants

from .router import router


# ------ 6. catch all text from user in state "waiting_for_shk" and send it to gpt 
@router.business_message(StateFilter(ClientStates.waiting_for_shk))
async def handle_unexpected_text_waiting_for_shk(
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
    user_data = await state.get_data()
    nm_id_name = user_data.get("nm_id_name")
    
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_feedback_and_before_shk_check_point(
        new_prompt=text,
        product_title=nm_id_name
    )
    await state.set_state(ClientStates.waiting_for_shk)
    msg = await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("shk", "разрезал(а) ШК")
    )
    await update_last_activity(state, msg)


# ------ 6. wait until user tap to button "Yes, cutted shk" and go to the state "waiting_for_photo_shk"
@router.callback_query(StateFilter(ClientStates.waiting_for_shk), F.data.startswith("shk_"))
async def handle_shk_answer(
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
            logging.info("cant delete message in q5")
    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )  
    
    msg = None
    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":  
        msg = await callback.message.answer(
            f"Когда разрежете этикетки от {nm_id_name}, нажмите, пожалуйста, на кнопку ниже", 
            reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
        )
        await state.set_state(ClientStates.waiting_for_shk)
        await update_last_activity(state, msg)
        return

    # дальше переходим в состояние waiting_for_photo_shk - ждем фотки разрезанных ШК
    msg = await callback.message.answer(
        f"Отправьте, пожалуйста, фотографию разрезанных этикеток"
    )
    await state.set_state(ClientStates.waiting_for_photo_shk)
    await update_last_activity(state, msg)
