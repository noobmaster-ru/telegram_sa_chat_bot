from aiogram import  F, types,  Bot
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.enums import ChatAction
from aiogram.methods import ReadBusinessMessage

from src.bot.states.user_flow import UserFlow
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass
from src.bot.utils.last_activity import update_last_activity

from .router import router

# ------ 2. catch all text from user in state "waiting_for_subcription_to_channel" and send it to gpt
@router.business_message(StateFilter(UserFlow.waiting_for_subcription_to_channel))
async def handle_unexpected_text_waiting_for_subcription_to_channel(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    CHANNEL_USERNAME: str,
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_agreement_and_before_subscription_point(
        new_prompt=text,
        CHANNEL_NAME=CHANNEL_USERNAME,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_subcription_to_channel)
    msg = await message.answer(
        f'{gpt_5_response}\nПока вы не подпишетесь на канал — раздача невозможна.\nПодпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:',
        reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
    )
    await update_last_activity(state, msg)

# ------ 2. wait until user tap to button "Yes, sub to channel"
@router.callback_query(StateFilter(UserFlow.waiting_for_subcription_to_channel), F.data.startswith("subscribe_"))
async def handle_subscription(
    callback: CallbackQuery,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    CHANNEL_USERNAME: str
):
    await callback.answer()
    telegram_id = callback.from_user.id
    value = "Да" if callback.data == "subscribe_yes" else "Нет"

    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    
    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name="subscribe",
        value=value,
        is_tap_to_keyboard=True
    )
    msg = None
    if callback.data == "subscribe_yes":
        # Проверяем подписку
        try:
            member = await callback.message.bot.get_chat_member(
                chat_id=CHANNEL_USERNAME,
                user_id=callback.from_user.id
            )
            if member.status in ("member", "administrator", "creator"):
                # Пользователь подписан → продолжаем
                await callback.message.edit_text(
                    "✅ Отлично! Вы подписаны на канал.",
                )
                # 👉 Начинаем пошаговый диалог
                msg = await callback.message.answer(
                    f"📦 Вы заказали товар `{nm_id}`?",  
                    reply_markup=get_yes_no_keyboard("order", "заказал(а)"),
                    parse_mode="MarkdownV2"
                )
                await state.set_state(UserFlow.waiting_for_order)
                await update_last_activity(state, msg)
                return
            else:
                try:
                    # Не подписан
                    msg = await callback.message.edit_text(
                        "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                        f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                        reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
                    )
                except:
                    msg = await callback.message.edit_text(
                        f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                        reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
                    )
                await update_last_activity(state, msg)
        except TelegramBadRequest:
            msg = await callback.message.answer(
                "⚠️ Не удалось проверить подписку. Проверьте, что бот — администратор канала."
            )
            await update_last_activity(state, msg)
    else:
        # Не подписан
        try:
            msg = await callback.message.edit_text(
                "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
            )
        except:
            msg = await callback.message.edit_text(
                f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
            )
        await state.set_state(UserFlow.waiting_for_subcription_to_channel)
        await update_last_activity(state, msg)