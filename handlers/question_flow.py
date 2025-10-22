from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, F

from google_sheets.google_sheets_class import GoogleSheetClass


from handlers.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
router = Router()

questions = [
    ("order", "📦 Вы заказали товар?"),
    ("receive", "📬 Вы получили товар?"),
    ("feedback", "💬 Вы оставили отзыв?"),
    ("shk", "✂️ ШК разрезали?")
]


# === Старт последовательных вопросов ===
async def start_buyer_flow(message: Message, spreadsheet: GoogleSheetClass, BUYERS_SHEET_NAME: str):
    """Запускает пошаговый опрос покупателя."""
    username = message.from_user.username or "без username"
    await message.answer("Продолжаем 👇")

    # # Сохраняем, что начали опрос (по желанию)
    # spreadsheet.update_buyer_button_status(
    #     sheet_name=BUYERS_SHEET_NAME,
    #     username=username,
    #     button_name="buyer_flow",
    #     value="начат"
    # )

    # Начинаем с первого вопроса
    await ask_next_question(message, spreadsheet, BUYERS_SHEET_NAME, 0)

async def ask_next_question(message, spreadsheet: GoogleSheetClass, BUYERS_SHEET_NAME: str, index: int):
    """Задаёт вопрос из списка по индексу."""
    if index >= len(questions):
        await message.answer("✅ Все ответы получены, спасибо!")
        return

    key, text = questions[index]
    await message.answer(text, reply_markup=get_yes_no_keyboard(key))

# ловит только те колбеки из questions
@router.callback_query(F.data.regexp(r"^(order|receive|feedback|shk)_(yes|no)$"))
async def handle_question_answer(callback: CallbackQuery, spreadsheet: GoogleSheetClass, BUYERS_SHEET_NAME: str):
    """Обработка нажатия кнопок Да/Нет"""
    username = callback.from_user.username or "без username"
    data = callback.data

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"

    # сохраняем ответ
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        username=username,
        button_name=key,
        value=value
    )

    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        await callback.message.answer("Пожалуйста, подтвердите действие.")
        await callback.message.answer(
            dict(questions)[key],
            reply_markup=get_yes_no_keyboard(key)
        )
        await callback.answer()
        return

    # если ответ "Да" → переходим к следующему вопросу
    current_index = next(i for i, (k, _) in enumerate(questions) if k == key)
    await ask_next_question(callback.message, spreadsheet, BUYERS_SHEET_NAME, current_index + 1)
    await callback.answer()