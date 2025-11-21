from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.states.client import ClientStates

from src.bot.utils.last_activity import update_last_activity
from .router import router


# catch all text waiting_for_photo_order, waiting_for_photo_feedback , waiting_for_photo_shk  and ask user to send photo!
@router.business_message(F.text, StateFilter(ClientStates.waiting_for_photo_order, ClientStates.waiting_for_photo_feedback, ClientStates.waiting_for_photo_shk))
async def handle_photo(message: Message, state: FSMContext):
    current_state = await state.get_state()
    business_connection_id = message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
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
    if current_state == ClientStates.waiting_for_photo_order:
        msg = await message.answer("Пришлите, пожалуйста, скриншот заказа.")
        await update_last_activity(state, msg)
    elif current_state == ClientStates.waiting_for_photo_feedback:
        msg = await message.answer("Пришлите, пожалуйста, скриншот отзыва на 5 звёзд.")
        await update_last_activity(state, msg)
    # current_state == ClientStates.waiting_for_photo_shk:
    else:
        msg = await message.answer("Пришлите, пожалуйста, фотографию разрезанных этикеток.")
        await update_last_activity(state, msg)

