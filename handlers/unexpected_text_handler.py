from handlers.states.user_flow import UserFlow
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram import Router, types

from handlers.states.user_flow import UserFlow
from google_sheets.google_sheets_class import GoogleSheetClass

from handlers.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from handlers.keyboards.get_subscription_check_keyboard import get_subscription_check_keyboard

from ai_module.open_ai_requests_class import OpenAiRequestClass

# Этот обработчик сработает, если пользователь напишет текст,
# пока бот ждёт нажатие кнопки в любом из заданных состояний.
router = Router()


# --- 1. Ожидание согласия на условия ---
@router.business_message(StateFilter(UserFlow.waiting_for_agreement))
async def handle_unexpected_text_waiting_for_agreement(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    client_gpt_5: OpenAiRequestClass,
    instruction_str: str,
):
    telegram_id = message.from_user.id
    text = message.text
    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id
    )
    gpt_5_response = await client_gpt_5.get_gpt_5_response_before_agreement_point(
        new_prompt=text,
        instruction_str=instruction_str
    )
    await message.answer(
        gpt_5_response, 
        reply_markup=get_yes_no_keyboard("agree")
    )
    # await message.answer(
    #     "Пожалуйста, используйте кнопки для ответа. Вы согласны на условия?",
    #     reply_markup=get_agreement_keyboard()
    # )

# --- 2. Ожидание подписки на канал ---
@router.business_message(StateFilter(UserFlow.waiting_for_subcription_to_channel))
async def handle_unexpected_text_waiting_for_subcription_to_channel(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    CHANNEL_USERNAME: str,
    client_gpt_5: OpenAiRequestClass,
    instruction_str: str
):
    telegram_id = message.from_user.id
    text = message.text
    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id
    )
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_agreement_and_before_subscription_point(
        new_prompt=text,
        instruction_str=instruction_str,
        CHANNEL_NAME=CHANNEL_USERNAME
    )
    await message.answer(
        f'{gpt_5_response}\nПока вы не подпишетесь на канал — раздача невозможна.\nПодпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:',
        reply_markup=get_subscription_check_keyboard()
    )


# --- 3. Ожидание подтверждения заказа ---
@router.business_message(StateFilter(UserFlow.waiting_for_order))
async def handle_unexpected_text_waiting_for_order(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    client_gpt_5: OpenAiRequestClass,
    instruction_str: str,
    CHANNEL_USERNAME: str
):
    telegram_id = message.from_user.id
    text = message.text
    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id
    )
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_agreement_and_before_subscription_point(
        new_prompt=text,
        instruction_str=instruction_str,
        CHANNEL_NAME=CHANNEL_USERNAME
    )
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("order")
    )

# --- 4. Ожидание подтверждения получения заказа ---
@router.business_message(StateFilter(UserFlow.waiting_for_order_receive))
async def handle_unexpected_text_waiting_for_order_receive(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    client_gpt_5: OpenAiRequestClass,
    instruction_str: str,
    CHANNEL_USERNAME: str
):
    telegram_id = message.from_user.id
    text = message.text
    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id
    )
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_order_and_before_receive_product_point(
        new_prompt=text,
        instruction_str=instruction_str,
        CHANNEL_NAME=CHANNEL_USERNAME
    )
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("receive")
    )


# --- 5. Ожидание подтверждения отзыва ---
@router.business_message(StateFilter(UserFlow.waiting_for_feedback))
async def handle_unexpected_text_waiting_for_feedback_done(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    client_gpt_5: OpenAiRequestClass,
    instruction_str: str,
    CHANNEL_USERNAME: str
):
    telegram_id = message.from_user.id
    text = message.text
    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id
    )
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_receive_product_and_before_feedback_check_point(
        new_prompt=text,
        instruction_str=instruction_str,
        CHANNEL_NAME=CHANNEL_USERNAME
    )
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("feedback")
    )



# --- 6. Ожидание подтверждения разрезанных ШК ---
@router.business_message(StateFilter(UserFlow.waiting_for_shk))
async def handle_unexpected_text_waiting_for_shk(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    client_gpt_5: OpenAiRequestClass,
    instruction_str: str,
    CHANNEL_USERNAME: str
):
    telegram_id = message.from_user.id
    text = message.text

    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id
    )
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_feedback_and_before_shk_check_point(
        new_prompt=text,
        instruction_str=instruction_str,
        CHANNEL_NAME=CHANNEL_USERNAME
    )
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("shk")
    )
