from aiogram.fsm.context import FSMContext

from aiogram.types import Message, CallbackQuery
from aiogram import Router, F

from google_sheets.google_sheets_class import GoogleSheetClass


from handlers.keyboards.get_yes_no_keyboard import get_yes_no_keyboard

from handlers.states.user_flow import UserFlow

router = Router()


async def ask_is_shk_cut_question(
    message: Message, 
    state: FSMContext
):
    await message.answer(
        "✂️ ШК разрезали?", 
        reply_markup=get_yes_no_keyboard("shk")
    )
    # переключаемся в состояние ожидания ответа на кнопку после "📦 Вы заказали товар?"
    await state.set_state(UserFlow.waiting_for_shk)

# Юзер после "✂️ ШК разрезали?" нажал на кнопку какую-то
@router.callback_query(F.data.startswith("shk_"))
async def handle_question_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str,
    state: FSMContext
):
    """Обработка нажатия кнопок Да/Нет"""
    username = callback.from_user.username or "без username"
    telegram_id = callback.from_user.id
    data = callback.data

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"

    # сохраняем ответ в гугл-таблицу
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
        button_name=key,
        value=value
    )

    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        await callback.message.answer(
            "✂️ ШК разрезали?", 
            reply_markup=get_yes_no_keyboard("shk")
        )
        await state.set_state(UserFlow.waiting_for_shk)
        await callback.answer()
        return

    # если ответ "Да" → переходим к следующему вопросу
    await callback.message.answer("✅ Все ответы получены, спасибо!")
    await callback.message.answer("☺️ Можете отправлять свои реквизиты: номер карты/номер телефона и сумму для оплаты. Мы свяжемся с вами через некоторое время.")
    await state.clear() # очищаем состояние
    return