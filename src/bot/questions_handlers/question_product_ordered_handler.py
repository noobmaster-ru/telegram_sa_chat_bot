from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from aiogram.filters import StateFilter
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow

from src.google_sheets.google_sheets_class import GoogleSheetClass

router = Router()

# Юзер после "📦 Вы заказали товар?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_order), F.data.startswith("order_"))
async def handle_order_answer(
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
        await callback.message.edit_text(
            "Когда закажете товар, нажмите на кнопку 'Да, заказал(а)'",
            reply_markup=get_yes_no_keyboard("order", "заказал(а)")
        )
        await state.set_state(UserFlow.waiting_for_order)
        return
    await callback.message.edit_text(
        "📬 Вы получили товар?", 
        reply_markup=get_yes_no_keyboard("receive", "получил(а)")
    )
    await state.set_state(UserFlow.waiting_for_order_receive)


# Юзер после "📬 Вы получили товар?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_order_receive),F.data.startswith("receive_"))
async def handle_receive_answer(
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
        await callback.message.edit_text(
            "Когда получите товар, нажмите на кнопку 'Да, получил(а)'", 
            reply_markup=get_yes_no_keyboard("receive", "получил(а)")
        )
        await state.set_state(UserFlow.waiting_for_order_receive)
        return
    # ✅ Следующий вопрос
    await callback.message.edit_text(
        "💬 Вы оставили отзыв?", 
        reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
    )
    await state.set_state(UserFlow.waiting_for_feedback)

    
# Юзер после "💬 Вы оставили отзыв?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_feedback), F.data.startswith("feedback_"))
async def handle_feedback_answer(
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
            "Когда оставите отзыв, нажмите на кнопку 'Да, оставил(а)'", 
            reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
        )
        await state.set_state(UserFlow.waiting_for_feedback)
        return
    # ✅ Следующий вопрос
    await callback.message.edit_text(
        "✂️ ШК разрезали?", 
        reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
    )
    await state.set_state(UserFlow.waiting_for_shk)


# Юзер после "✂️ ШК разрезали?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_shk), F.data.startswith("shk_"))
async def handle_shk_answer(
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
        await callback.message.edit_text(
            "Когда разрежите ШК, нажмите на кнопку 'Да, разрезал(а)'", 
            reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
        )
        await state.set_state(UserFlow.waiting_for_shk)
        return
    # ✅ Завершение опроса
    await callback.message.edit_text("✅ Все ответы получены, спасибо!")
    # await callback.message.answer("✅ Все ответы получены, спасибо!")
    await callback.message.answer("☺️ Можете отправлять свои реквизиты: номер карты/телефона и сумму для оплаты. Мы свяжемся с вами через некоторое время.")
    await state.set_state(UserFlow.waiting_for_requisites)