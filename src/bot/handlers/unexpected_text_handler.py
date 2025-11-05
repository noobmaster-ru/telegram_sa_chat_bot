from aiogram import Router, types
from aiogram.filters import StateFilter,  Command
from aiogram.fsm.context import FSMContext

from src.bot.states.user_flow import UserFlow
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass

# Этот обработчик сработает, если пользователь напишет текст,
# пока бот ждёт нажатие кнопки в любом из заданных состояний.
router = Router()

    
# --- 1. Ожидание согласия на условия ---
@router.business_message(StateFilter(UserFlow.waiting_for_agreement))
async def handle_unexpected_text_waiting_for_agreement(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext,
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_before_agreement_point(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_agreement)
    await message.answer(
        gpt_5_response, 
        reply_markup=get_yes_no_keyboard("agree","согласен(на)")
    )

# --- 2. Ожидание подписки на канал ---
@router.business_message(StateFilter(UserFlow.waiting_for_subcription_to_channel))
async def handle_unexpected_text_waiting_for_subcription_to_channel(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    CHANNEL_USERNAME: str,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_agreement_and_before_subscription_point(
        new_prompt=text,
        CHANNEL_NAME=CHANNEL_USERNAME,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_subcription_to_channel)
    await message.answer(
        f'{gpt_5_response}\nПока вы не подпишетесь на канал — раздача невозможна.\nПодпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:',
        reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
    )


# --- 3. Ожидание подтверждения заказа ---
@router.business_message(StateFilter(UserFlow.waiting_for_order))
async def handle_unexpected_text_waiting_for_order(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_subscription_and_before_order_point(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_order)
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("order", "заказал(а)")
    )

# --- 4. Ожидание подтверждения получения заказа ---
@router.business_message(StateFilter(UserFlow.waiting_for_order_receive))
async def handle_unexpected_text_waiting_for_order_receive(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_order_and_before_receive_product_point(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_order_receive)
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("receive", "получил(а)")
    )


# --- 5. Ожидание подтверждения отзыва ---
@router.business_message(StateFilter(UserFlow.waiting_for_feedback))
async def handle_unexpected_text_waiting_for_feedback_done(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_receive_product_and_before_feedback_check_point(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_feedback)
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("feedback", "оставил(а) отзыв")
    )


# --- 6. Ожидание подтверждения разрезанных ШК ---
@router.business_message(StateFilter(UserFlow.waiting_for_shk))
async def handle_unexpected_text_waiting_for_shk(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass,
    state: FSMContext
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
    gpt_5_response = await client_gpt_5.get_gpt_5_response_after_feedback_and_before_shk_check_point(
        new_prompt=text,
        nm_id=nm_id,
        count=nm_id_amount
    )
    await state.set_state(UserFlow.waiting_for_shk)
    await message.answer(
        gpt_5_response,
        reply_markup=get_yes_no_keyboard("shk", "разрезал(а) ШК")
    )
