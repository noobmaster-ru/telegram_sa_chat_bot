from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from aiogram.methods import ReadBusinessMessage


from src.bot.states.user_flow import UserFlow

from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass

from .router import router

from src.core.config import settings


@router.business_message(StateFilter("generating"))
async def wait_response(message: Message):
    business_connection_id = message.business_connection_id
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    await message.answer("Ожидайте ответа, пожалуйста ...")


@router.business_message(StateFilter(UserFlow.continue_dialog))
async def handle_messages_after_requisites(
    message: Message, 
    state: FSMContext, 
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass
):
    telegram_id = message.from_user.id
    text = message.text if message.text else "(без текста)"

    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    nm_id_amount = user_data.get("nm_id_amount")
    
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    business_connection_id = message.business_connection_id
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    if "?" in text: 
        # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
        await state.set_state('generating')   
        gpt5_response_text = await client_gpt_5.create_gpt_5_response(
            new_prompt=text,
            nm_id=nm_id,
            count=nm_id_amount
        )
        await state.set_state(UserFlow.continue_dialog)
        await message.answer(gpt5_response_text)
    else:
        if len(text) > settings.MIN_LEN_TEXT:
            await state.set_state('generating')
            gpt5_response_text = await client_gpt_5.create_gpt_5_response(
                new_prompt=text,
                nm_id=nm_id,
                count=nm_id_amount
            )
            await state.set_state(UserFlow.continue_dialog)
            await message.answer(gpt5_response_text)    
        elif text in settings.OK_WORDS:
            await message.answer("👍")
        else:
            await message.answer("Напишите, пожалуйста, ваш вопрос более подробнее, одним сообщением")
