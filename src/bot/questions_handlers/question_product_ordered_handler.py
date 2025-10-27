from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext


from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow
from src.bot.questions_handlers.questiong_order_receive_handler import ask_is_product_receive_question

from src.google_sheets.google_sheets_class import GoogleSheetClass

router = Router()


async def ask_is_product_ordered_question(
    message: Message, 
    state: FSMContext
):
    await message.answer(
        "📦 Вы заказали товар?", 
        reply_markup=get_yes_no_keyboard("order", "заказал(а)")
    )
    # переключаемся в состояние ожидания ответа на кнопку после "📦 Вы заказали товар?"
    await state.set_state(UserFlow.waiting_for_order)

# Юзер после "📦 Вы заказали товар?" нажал на кнопку какую-то
@router.callback_query(F.data.startswith("order_"))
async def handle_question_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str,
    state: FSMContext
):
    """Обработка нажатия кнопок Да/Нет"""
    telegram_id = callback.from_user.id
    data = callback.data

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"

    # сохраняем ответ в гугл-таблицу
    await spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
        button_name=key,
        value=value
    )

    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        await callback.message.answer(
            "📦 Вы заказали товар?",
            reply_markup=get_yes_no_keyboard("order","заказал(а)")
        )
        await state.set_state(UserFlow.waiting_for_order)
        await callback.answer()
        return

    # если ответ "Да" → переходим к следующему вопросу
    await ask_is_product_receive_question(callback.message, state)
    await callback.answer()