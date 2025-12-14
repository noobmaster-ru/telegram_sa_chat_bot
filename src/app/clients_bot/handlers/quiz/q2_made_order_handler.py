import logging
from aiogram import F,  types, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.enums import ChatAction
from aiogram.methods import ReadBusinessMessage


from src.app.bot.states.client import ClientStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.utils.last_activity import update_last_activity
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.infrastructure.apis.open_ai_requests_class import OpenAiRequestClass
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

# ------ 3. catch all text from user in state "waiting_for_order" and send it to gpt 
@router.business_message(StateFilter(ClientStates.waiting_for_order))
async def handle_unexpected_text_waiting_for_order(
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
    instruction = user_data.get("instruction")
    
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_subscription_and_before_order_point(
        new_prompt=text,
        instruction=instruction
    )
    await state.set_state(ClientStates.waiting_for_order)
    msg = await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("order", "заказал(а)")
    )
    await update_last_activity(state, msg)

# ------ 3. wait until user tap to button "Yes, ordered" and go to state "waiting_for_photo_order"
@router.callback_query(StateFilter(ClientStates.waiting_for_order), F.data.startswith("order_"))
async def handle_order_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    state: FSMContext,
):
    await callback.answer()
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
    nm_id = client_data.get("nm_id")
    nm_id_name = client_data.get("nm_id_name")

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )
    # если ответ "Нет" → задаём тот же вопрос ещё раз
    msg = None
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
            logging.info("cant delete messages in q2")
    if value == "Нет":
        text = f"Когда закажете товар {nm_id_name}, нажмите, пожалуйста, на кнопку ниже"
        msg = await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            reply_markup=get_yes_no_keyboard("order", "заказал(а)"),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_order)
        await update_last_activity(state, msg)
        return
    
    # дальше переходим в состояние waiting_for_photo_order - ждем фотки заказа от юзера
    text = f"Отправьте, пожалуйста, *скриншот* сделанного заказа"
    msg = await callback.message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )
    await state.set_state(ClientStates.waiting_for_photo_order)
    await update_last_activity(state, msg)