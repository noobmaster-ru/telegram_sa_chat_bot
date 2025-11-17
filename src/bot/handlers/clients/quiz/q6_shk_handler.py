from aiogram import F, Bot, types
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage
from aiogram.types import  CallbackQuery


from src.bot.states.client import ClientStates
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass
from src.bot.utils.last_activity import update_last_activity

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
    telegram_id = message.from_user.id
    text = message.text
    
    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    nm_id_amount = user_data.get("nm_id_amount")
    
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    await state.set_state('generating')
    # помечаем сообщение как прочитанное
    business_connection_id = message.business_connection_id
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
        nm_id=nm_id,
        count=nm_id_amount
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

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"
    
    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )  
    
    msg = None
    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":  
        try:
            msg = await callback.message.edit_text(
                f"Когда разрежете ШК от {nm_id}, нажмите на кнопку 'Да, разрезал(а)'", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
            )
            await state.set_state(ClientStates.waiting_for_shk)
            await update_last_activity(state, msg)
            return
        except:
            msg = await callback.message.edit_text(
                f"Нужно разрезать ШК товара {nm_id}, затем нажмите на кнопку 'Да, разрезал(а)'", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
            )
            await state.set_state(ClientStates.waiting_for_shk)
            await update_last_activity(state, msg)
            return
    
    # дальше переходим в состояние waiting_for_photo_shk - ждем фотки разрезанных ШК
    msg = await callback.message.edit_text(
        f"Отправьте, пожалуйста, фотографию разрезанных ШК."
    )
    await state.set_state(ClientStates.waiting_for_photo_shk)
    await update_last_activity(state, msg)
