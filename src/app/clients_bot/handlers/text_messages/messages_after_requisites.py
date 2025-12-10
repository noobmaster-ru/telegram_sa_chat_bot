from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from aiogram.methods import ReadBusinessMessage


from src.app.bot.states.client import ClientStates
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.infrastructure.apis.open_ai_requests_class import OpenAiRequestClass
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router


@router.business_message(StateFilter(ClientStates.continue_dialog))
async def handle_messages_after_requisites(
    message: Message, 
    state: FSMContext, 
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass
):
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    telegram_id = message.from_user.id
    text = message.text if message.text else "(без текста)"

    user_data = await state.get_data()
    instruction = user_data.get("instruction")
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        text=text
    )
    business_connection_id = message.business_connection_id
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
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    if "?" in text: 
        # переключаем в состояние ожидания(пока ответ от гпт не сформировался) 
        gpt5_response_text = await client_gpt_5.create_gpt_5_response(
            new_prompt=text,
            instruction=instruction
        )
        await message.answer(gpt5_response_text)
        await state.set_state(ClientStates.continue_dialog)
    else:
        if len(text) > constants.MIN_LEN_TEXT:
            gpt5_response_text = await client_gpt_5.create_gpt_5_response(
                new_prompt=text,
                instruction=instruction
            )
            await message.answer(gpt5_response_text)    
            await state.set_state(ClientStates.continue_dialog)
        elif text in constants.OK_WORDS:
            await message.answer("👍")
            await state.set_state(ClientStates.continue_dialog)
        else:
            text_answer = "Напишите, пожалуйста, ваш вопрос более подробнее, одним сообщением"
            await message.answer(
                text=StringConverter.escape_markdown_v2(text_answer),
                parse_mode="MarkdownV2"
            )
            await state.set_state(ClientStates.continue_dialog)
