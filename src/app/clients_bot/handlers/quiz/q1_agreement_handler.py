import logging
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from aiogram import F, types, Bot
from aiogram.enums import ChatAction
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage
from aiogram.filters import StateFilter

from src.app.bot.states.client import ClientStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.utils.last_activity import update_last_activity
from src.app.bot.utils.leads import consume_lead_for_cabinet

from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.infrastructure.apis.open_ai_requests_class import OpenAiRequestClass
from src.infrastructure.db.models import CabinetORM
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

# ------ 1. catch all text from user in state "waiting_for_agreement" and send it to gpt 
@router.business_message(StateFilter(ClientStates.waiting_for_agreement))
async def handle_unexpected_text_waiting_for_agreement(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    cabinet: CabinetORM,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext,
    bot: Bot
):
    await state.set_state(constants.SKIP_MESSAGE_STATE)

    
    telegram_id = message.from_user.id
    text = message.text
    business_connection_id = message.business_connection_id
    
    user_data = await state.get_data()
    instruction = user_data.get("instruction")

    
    # Обновляем время последнего сообщения в ТАБЛИЦЕ КОНКРЕТНОГО КАБИНЕТА
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
    
    # GPT-ответ с учётом конкретного продукта (nm_id_name для данного кабинета)
    gpt_5_response = await client_gpt_5.get_gpt_5_response_before_agreement_point(
        new_prompt=text,
        instruction=instruction
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
    cabinet: CabinetORM,              # <- тоже можем принять, чтобы при необходимости работать по кабинету
    redis: Redis,
    db_session_factory: async_sessionmaker
):
    await callback.answer()
    
    if cabinet is None or spreadsheet is None:
        text = "Техническая ошибка: кабинет ещё не привязан, попробуйте позже."
        await callback.message.answer(
            text = StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return
    
    telegram_id = callback.from_user.id
    business_connection_id = callback.message.business_connection_id
    
    if business_connection_id:
        await state.update_data(business_connection_id=business_connection_id)
    
    value = "Да" if callback.data == "agree_yes" else "Нет"
    client_data = await state.get_data()
    nm_id_name = client_data.get("nm_id_name")
    messages_ids_to_delete = client_data.get("last_messages_ids",[])

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name="agree",
        value=value,
        is_tap_to_keyboard=True
    )
    # ====== ВЕТКА "СОГЛАСЕН" ======
    if callback.data == "agree_yes":
        try:
            # 👉 ТУТ СПИСЫВАЕМ ЛИД
            await consume_lead_for_cabinet(
                redis_client=redis,
                session_factory=db_session_factory,
                cabinet=cabinet,
                client_id=callback.from_user.id,
                bot_id=callback.bot.id,
                business_connection_id=business_connection_id,
                # cabinet_cache=self._cabinet_cache  # если захочешь передавать из middleware
            )
        except:
            pass
        text = "Спасибо за согласие с нашими условиями!"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
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

        # 👉 Начинаем пошаговый диалог
        text = f"📦 Вы заказали {nm_id_name}?"
        msg = await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),  
            reply_markup=get_yes_no_keyboard("order", "заказал(а)"),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_order)
        await update_last_activity(state, msg)
        return 
    
    # ====== ВЕТКА "НЕ СОГЛАСЕН" ======
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
        text = "Без согласия, к сожалению, кэшбек невозможен 😔 Вы согласны на наши условия?"
        msg = await callback.message.answer(
            text = StringConverter.escape_markdown_v2(text),
            reply_markup=get_yes_no_keyboard("agree", "согласен(на)"),
            parse_mode="MarkdownV2"
        )
        await state.set_state(ClientStates.waiting_for_agreement)
        await update_last_activity(state, msg)
        return 