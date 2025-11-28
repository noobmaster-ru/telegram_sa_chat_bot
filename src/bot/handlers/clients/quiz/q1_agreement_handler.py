import logging
from aiogram import F, types, Bot
from aiogram.enums import ChatAction
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage
from aiogram.filters import StateFilter


from src.bot.states.client import ClientStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.keyboards.inline.get_sub_to_channel_keyboard import get_sub_to_channel
from src.apis.google_sheets_class import GoogleSheetClass
from src.apis.open_ai_requests_class import OpenAiRequestClass
from src.bot.utils.last_activity import update_last_activity
from src.core.config import constants
from .router import router


# ------ 1. catch all text from user in state "waiting_for_agreement" and send it to gpt 
@router.business_message(StateFilter(ClientStates.waiting_for_agreement))
async def handle_unexpected_text_waiting_for_agreement(
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
        await state.update_data(business_connection_id=business_connection_id)
    
    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    nm_id_amount = user_data.get("nm_id_amount")
    
    
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_before_agreement_point(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(ClientStates.waiting_for_agreement)
    msg = await message.answer(
        gpt_5_response, 
        reply_markup=get_yes_no_keyboard("agree","согласен(на)")
    )
    await update_last_activity(state, msg)
    
# ------ 1. wait until user tap to button "Yes, agree"
@router.callback_query(StateFilter(ClientStates.waiting_for_agreement), F.data.startswith("agree_"))
async def handle_agreement(
    callback: CallbackQuery,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    CHANNEL_USERNAME: str,
    bot: Bot
):
    await callback.answer()
    telegram_id = callback.from_user.id
    business_connection_id = callback.message.business_connection_id
    if business_connection_id:
        await state.update_data(
            business_connection_id=business_connection_id
        )
    value = "Да" if callback.data == "agree_yes" else "Нет"
    client_data = await state.get_data()
    nm_id = client_data.get("nm_id")
    messages_ids_to_delete = client_data["last_messages_ids"]

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name="agree",
        value=value,
        is_tap_to_keyboard=True
    )
    if callback.data == "agree_yes":
        await callback.message.answer("Спасибо!")
        if messages_ids_to_delete:
            try:
                await callback.bot.delete_business_messages(
                    business_connection_id=business_connection_id,
                    message_ids=messages_ids_to_delete
                )
                await state.update_data(last_messages_ids=[])
            except:
                await state.update_data(last_messages_ids=[])
                logging.info("cant delete message in q1")
        # check subscribe to channel 
        member = await bot.get_chat_member(
            chat_id=constants.CHANNEL_USERNAME_STR,
            user_id=callback.from_user.id
        )
        if not member.status in ("member", "administrator", "creator"):
            # Не подписан
            await callback.message.answer(
                f"Подпишитесь на наш канал {CHANNEL_USERNAME}, там будет информация о новых раздачах 🙃",
                reply_markup=get_sub_to_channel()
            )
        else:
            await callback.message.answer(
                "✅ Отлично! Вы подписаны на наш канал. Там будет информация о новых раздачах 🙃",
            )
            await spreadsheet.update_buyer_button_and_time(
                telegram_id=telegram_id,
                button_name="subscribe",
                value="Да",
                is_tap_to_keyboard=True
            )
        # 👉 Начинаем пошаговый диалог
        msg = await callback.message.answer(
            f"📦 Вы заказали товар {nm_id}?",  
            reply_markup=get_yes_no_keyboard("order", "заказал(а)")
        )
        await state.set_state(ClientStates.waiting_for_order)
        await update_last_activity(state, msg)
        return 
    else:
        if messages_ids_to_delete:
            try:
                await callback.bot.delete_business_messages(
                    business_connection_id=business_connection_id,
                    message_ids=messages_ids_to_delete
                )
                await state.update_data(last_messages_ids=[])
            except: 
                await state.update_data(last_messages_ids=[])
                logging.info("cant delete messages in q1")
        msg = await callback.message.answer(
            "Без согласия , кэшбек невозможен 😔 Вы согласны на наши условия?",
            reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
        )
        await state.set_state(ClientStates.waiting_for_agreement)
        await update_last_activity(state, msg)
        return 