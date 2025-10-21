from aiogram import Router, F
from aiogram.types import CallbackQuery
from google_sheets.google_sheets_class import GoogleSheetClass
from handlers.keyboards import get_different_number_of_buttons_keyboard

router = Router()

# ==== Обработка нажатий на кнопки ====
@router.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "feedback_yes" else "Нет"
    
    # обновляем статус "Отзыв оставлен"
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username, 
        button_name="feedback", 
        value=value
    )
    
    # генерируем новые кнопки только для оставшихся
    remaining_buttons = spreadsheet.get_remaining_buttons(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username
    )
    if remaining_buttons:
        await callback.message.answer(
            f"✅ Ваш ответ '{value}' зафиксирован.",
            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
        )
    else:
        await callback.message.answer("✅ Все статусы заполнены, спасибо!")

    await callback.answer()


@router.callback_query(F.data.startswith("order_"))
async def handle_order(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "order_yes" else "Нет"
    
    # обновляем статус "Заказ сделан"
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username, 
        button_name="order", 
        value=value
    )
    
    # генерируем новые кнопки только для оставшихся
    remaining_buttons = spreadsheet.get_remaining_buttons(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username
    )
    if remaining_buttons:
        await callback.message.answer(
            f"✅ Ваш ответ '{value}' зафиксирован.",
            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
        )
    else:
        await callback.message.answer("✅ Все статусы заполнены, спасибо!")

    await callback.answer()


@router.callback_query(F.data.startswith("shk_"))
async def handle_shk(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "shk_yes" else "Нет"
    
    # обновляем статус "ШК разрезан"
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username, 
        button_name="shk", 
        value=value
    )
    
    # генерируем новые кнопки только для оставшихся
    remaining_buttons = spreadsheet.get_remaining_buttons(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username
    )
    if remaining_buttons:
        await callback.message.answer(
            f"✅ Ваш ответ '{value}' зафиксирован.",
            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
        )
    else:
        await callback.message.answer("✅ Все статусы заполнены, спасибо!")
    await callback.answer()
