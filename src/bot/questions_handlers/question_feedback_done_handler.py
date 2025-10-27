from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram import Router, F


from src.google_sheets.google_sheets_class import GoogleSheetClass
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow
from src.bot.questions_handlers.question_shk_handler import ask_is_shk_cut_question

router = Router()

async def ask_is_feedback_done_question(
    callback: CallbackQuery, 
    state: FSMContext
):
    await callback.message.edit_text(
        "💬 Вы оставили отзыв?", 
        reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
    )
    # переключаемся в состояние ожидания ответа на кнопку после "📦 Вы заказали товар?"
    await state.set_state(UserFlow.waiting_for_feedback)

# Юзер после "💬 Вы оставили отзыв?" нажал на кнопку какую-то
@router.callback_query(F.data.startswith("feedback_"))
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
            "💬 Вы оставили отзыв?", 
            reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
        )
        await state.set_state(UserFlow.waiting_for_feedback)
        return

    # если ответ "Да" → переходим к следующему вопросу
    await ask_is_shk_cut_question(callback, state)