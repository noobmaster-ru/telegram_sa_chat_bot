from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from aiogram.filters import StateFilter
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow

from src.services.google_sheets_class import GoogleSheetClass

router = Router()

# Юзер после "📦 Вы заказали товар?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_order), F.data.startswith("order_"))
async def handle_order_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str,
    state: FSMContext,
):
    await callback.answer()
    """Обработка нажатия кнопок Да/Нет"""
    telegram_id = callback.from_user.id
    data = callback.data

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"

    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )
    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        try:
            await callback.message.edit_text(
                f"Когда закажете товар {nm_id}, нажмите на кнопку 'Да, заказал(а)'",
                reply_markup=get_yes_no_keyboard("order", "заказал(а)")
            )
        except:
            await callback.message.edit_text(
                f"Нужно заказать товар {nm_id}, когда закажете товар - нажмите на кнопку 'Да, заказал(а)'",
                reply_markup=get_yes_no_keyboard("order", "заказал(а)")
            )
        await state.set_state(UserFlow.waiting_for_order)
        return
    await callback.message.edit_text(
        f"📬 Вы получили товар {nm_id}?", 
        reply_markup=get_yes_no_keyboard("receive", "получил(а)")
    )
    await state.set_state(UserFlow.waiting_for_order_receive)


# Юзер после "📬 Вы получили товар?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_order_receive), F.data.startswith("receive_"))
async def handle_receive_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str,
    state: FSMContext,
):
    await callback.answer()
    """Обработка нажатия кнопок Да/Нет"""
    telegram_id = callback.from_user.id
    data = callback.data

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"

    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    

    
 
    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )
    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        try:
            await callback.message.edit_text(
                f"Когда получите товар {nm_id}, нажмите на кнопку 'Да, получил(а)'", 
                reply_markup=get_yes_no_keyboard("receive", "получил(а)")
            )
        except:
            await callback.message.edit_text(
                f"Нужно получить товар {nm_id}, после - нажмите на кнопку 'Да, получил(а)'",
                reply_markup=get_yes_no_keyboard("receive", "получил(а)")
            )
        await state.set_state(UserFlow.waiting_for_order_receive)
        return
    # ✅ Следующий вопрос
    await callback.message.edit_text(
        f"💬 Вы оставили отзыв на {nm_id}?", 
        reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
    )
    await state.set_state(UserFlow.waiting_for_feedback)

    
# Юзер после "💬 Вы оставили отзыв?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_feedback), F.data.startswith("feedback_"))
async def handle_feedback_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str,
    state: FSMContext,
):
    await callback.answer()
    """Обработка нажатия кнопок Да/Нет"""
    telegram_id = callback.from_user.id
    data = callback.data

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"
    
    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )
    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        try:
            await callback.message.edit_text(
                f"Когда оставите отзыв на товар {nm_id}, нажмите на кнопку 'Да, оставил(а)'", 
                reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
            )
        except:
            await callback.message.edit_text(
                f"Нужно оставить отзыв 5 звезд на товар {nm_id}, затем нажмите на кнопку 'Да, оставил(а)'", 
                reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
            )
        await state.set_state(UserFlow.waiting_for_feedback)
        return
    # ✅ Следующий вопрос
    await callback.message.edit_text(
        f"✂️ ШК разрезали на {nm_id}?", 
        reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
    )
    await state.set_state(UserFlow.waiting_for_shk)


# Юзер после "✂️ ШК разрезали?" нажал на кнопку какую-то
@router.callback_query(StateFilter(UserFlow.waiting_for_shk), F.data.startswith("shk_"))
async def handle_shk_answer(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str,
    state: FSMContext,
):
    await callback.answer()
    """Обработка нажатия кнопок Да/Нет"""
    telegram_id = callback.from_user.id
    data = callback.data

    key = data.split("_")[0]
    value = "Да" if data.endswith("_yes") else "Нет"
    
    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name=key,
        value=value,
        is_tap_to_keyboard=True
    )  
    

    # если ответ "Нет" → задаём тот же вопрос ещё раз
    if value == "Нет":
        try:
            await callback.message.edit_text(
                f"Когда разрежете ШК от {nm_id}, нажмите на кнопку 'Да, разрезал(а)'", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
            )
        except:
            await callback.message.edit_text(
                f"Нужно разрезать ШК товара {nm_id}, затем нажмите на кнопку 'Да, разрезал(а)'", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
            )
        await state.set_state(UserFlow.waiting_for_shk)
        return
    
    # ✅ Завершение опроса
    await callback.message.edit_text("✅ Все ответы получены, спасибо!")
    await callback.message.answer("☺️ Можете отправлять свои реквизиты:\n- Номер карты: AAAA BBBB CCCC DDDD или\n- Номер телефона: 8910XXXXXXX \n- Название банка: Сбербанк, Т-банк\n-Cумму для оплаты: 500 рублей\nМы свяжемся с вами через некоторое время,спасибо")
    await state.set_state(UserFlow.waiting_for_requisites)