from aiogram import F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.states.user_flow import UserFlow

from src.bot.utils.last_activity import update_last_activity
from .router import router


# catch all text waiting_for_photo_order, waiting_for_photo_feedback , waiting_for_photo_shk  and ask user to send photo!
@router.business_message(F.text, StateFilter(UserFlow.waiting_for_photo_order, UserFlow.waiting_for_photo_feedback, UserFlow.waiting_for_photo_shk))
async def handle_photo(message: Message, state: FSMContext):
    await update_last_activity(state, message)
    current_state = await state.get_state() 
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
    if current_state == UserFlow.waiting_for_photo_order:
        await message.answer("Пришлите, пожалуйста, скриншот заказа.")
    elif current_state == UserFlow.waiting_for_photo_feedback:
        await message.answer("Пришлите, пожалуйста, скриншот отзыва на 5 звёзд.")
    # current_state == UserFlow.waiting_for_photo_shk:
    else:
        await message.answer("Пришлите, пожалуйста, фотографию разрезанных этикеток.")

