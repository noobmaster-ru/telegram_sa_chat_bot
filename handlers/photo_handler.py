# handlers/photo_handler.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from handlers.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from google_sheets.google_sheets_class import GoogleSheetClass
router = Router()


# --- FSM состояния ---
class PhotoStates(StatesGroup):
    waiting_for_photo_confirmation = State()
    photo_type = State()  # "order" или "shk"

# ==== Получение фото от пользователя ==== !!! bussiness_message!!!!
@router.business_message(F.photo)
async def handle_photo(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    ADMIN_ID_LIST: list
):
    user_data = await state.get_data()
    telegram_id = message.from_user.id
    username = message.from_user.username or "без username"
    photo_type = user_data.get("photo_type", "order")  # по умолчанию ждём фото заказа
    if telegram_id in ADMIN_ID_LIST:
        # обновляем время последнего сообщения
        spreadsheet.update_buyer_last_time_message(
            sheet_name=BUYERS_SHEET_NAME,
            telegram_id=telegram_id
        )
        if photo_type == "order":
            # спрашиваем подтверждение, что это фото заказа
            await message.answer(
                "📸 Это скрин заказа?",
                reply_markup=get_yes_no_keyboard(
                    callback_prefix="photo_order_", 
                    statement="скрин заказа"
                )
            )
        elif photo_type == "shk":
            # спрашиваем подтверждение, что это фото разрезанного ШК
            await message.answer(
                "📸 Это скрин разрезанного ШК?",
                reply_markup=get_yes_no_keyboard(
                    callback_prefix="photo_shk_",
                    statement="скрин разрезанного ШК")
            )
        else:
            await message.answer("⚠️ Неизвестный тип фото. Пожалуйста, следуйте инструкциям.")

# ==== Обработка кнопок Да/Нет для фото заказа ====
@router.callback_query(F.data.startswith("photo_order_"))
async def handle_photo_order(callback: CallbackQuery, state: FSMContext):
    answer = "yes" if callback.data.endswith("yes") else "no"
    username = callback.from_user.username or "без username"

    if answer == "yes":
        await callback.message.answer("✅ Фото заказа принято!")
        # теперь ждём фото ШК
        await state.update_data(photo_type="shk")
    else:
        await callback.message.answer("❌ Фото заказа не принято. Попробуйте прислать корректное фото.")

    await callback.answer()

# ==== Обработка кнопок Да/Нет для фото ШК ====
@router.callback_query(F.data.startswith("photo_shk_"))
async def handle_photo_shk(callback: CallbackQuery, state: FSMContext):
    answer = "yes" if callback.data.endswith("yes") else "no"
    username = callback.from_user.username or "без username"

    if answer == "yes":
        await callback.message.answer("✅ Фото разрезанного ШК принято!")
        await state.clear()  # flow завершен, очищаем state
    else:
        await callback.message.answer("❌ Фото ШК не принято. Попробуйте прислать корректное фото.")

    await callback.answer()
