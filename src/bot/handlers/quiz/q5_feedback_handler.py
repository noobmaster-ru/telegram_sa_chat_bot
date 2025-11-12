from aiogram import F, types, Bot
from aiogram.enums import ChatAction
from aiogram.types import  CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage
from aiogram.filters import StateFilter

from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow
from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass
from src.bot.utils.last_activity import update_last_activity

from .router import router

# ------ 5. catch all text from user in state "waiting_for_feedback" and send it to gpt 
@router.business_message(StateFilter(UserFlow.waiting_for_feedback))
async def handle_unexpected_text_waiting_for_feedback_done(
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_receive_product_and_before_feedback_check_point(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_feedback)
    msg = await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("feedback", "оставил(а) отзыв")
    )
    await update_last_activity(state, msg)

# ------ 5. wait until user tap to button "Yes, made feedback" and go to the state "waiting_for_photo_feedback"
@router.callback_query(StateFilter(UserFlow.waiting_for_feedback), F.data.startswith("feedback_"))
async def handle_feedback_answer(
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
                f"Когда оставите отзыв на товар [{nm_id}](https://www\\.wildberries\\.ru/catalog/{nm_id}/detail\\.aspx\\?targetUrl=SP), нажмите на кнопку 'Да, оставил(а)'", 
                reply_markup=get_yes_no_keyboard("feedback", "оставил(а)"),
                parse_mode="MarkdownV2"
            )
        except:
            msg = await callback.message.edit_text(
                f"Нужно оставить отзыв 5 звезд на товар [{nm_id}](https://www\\.wildberries\\.ru/catalog/{nm_id}/detail\\.aspx\\?targetUrl=SP), затем нажмите на кнопку 'Да, оставил(а)'", 
                reply_markup=get_yes_no_keyboard("feedback", "оставил(а)"),
                parse_mode="MarkdownV2"
            )
        await state.set_state(UserFlow.waiting_for_feedback)
        await update_last_activity(state, msg)
        return
    
    # дальше переходим в состояние waiting_for_photo_feedback - ждем фотки отзыва от юзера
    msg = await callback.message.edit_text(
        f"Отправьте, пожалуйста скриншот отзыва на 5 звёзд"
    )
    await state.set_state(UserFlow.waiting_for_photo_feedback)
    await update_last_activity(state, msg)
   