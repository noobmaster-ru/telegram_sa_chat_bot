from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import logging
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.google_sheets_class import GoogleSheetClass
from src.bot.states.user_flow import UserFlow


from src.bot.handlers.message_handler import is_known_user
import redis.asyncio as asyncredis

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
    ADMIN_ID_LIST: list,
    redis: asyncredis,
    REDIS_KEY_SET_USERS_ID: str
):
    user_data = await state.get_data()
    telegram_id = message.from_user.id
    photo_type = user_data.get("photo_type", "order")  # по умолчанию ждём фото заказа
    
    # уже писал нам — пропускаем
    if await is_known_user(redis, REDIS_KEY_SET_USERS_ID, telegram_id):
        logging.info(f"{telegram_id} in redis database , skip")
        await message.answer()
        return
    
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(telegram_id=telegram_id)
    
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
    # other type
    else:
        await message.edit_text("⚠️ Неизвестный тип фото. Пожалуйста, следуйте инструкциям.")

# ==== Обработка кнопок Да/Нет для фото заказа ====
@router.callback_query(F.data.startswith("photo_order_"))
async def handle_photo_order(
    callback: CallbackQuery,
    state: FSMContext,
    CHANNEL_USERNAME: str,
    nm_id: str
):
    answer = "yes" if callback.data.endswith("yes") else "no"
    username = callback.from_user.username or "без username"

    if answer == "yes":
        await callback.message.edit_text("✅ Фото заказа принято!")
        # теперь ждём фото ШК
        await state.update_data(photo_type="shk")
        current_state = await state.get_state() 
        if current_state == UserFlow.waiting_for_agreement:
            await callback.message.answer(
                "Согласны на условия?",
                reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
            )
            await state.set_state(UserFlow.waiting_for_agreement)
        elif current_state == UserFlow.waiting_for_subcription_to_channel:
            # Не подписан
            await callback.message.edit_text(
                "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
            )
            await state.set_state(UserFlow.waiting_for_subcription_to_channel)
        elif current_state == UserFlow.waiting_for_order:
            # 👉 Начинаем пошаговый диалог
            await callback.message.edit_text(
                f"📦 Вы заказали товар {nm_id}?", 
                reply_markup=get_yes_no_keyboard("order", "заказал(а)")
            )
            await state.set_state(UserFlow.waiting_for_order)
        elif current_state == UserFlow.waiting_for_order_receive:
            await callback.message.edit_text(
                f"📬 Вы получили товар {nm_id}?", 
                reply_markup=get_yes_no_keyboard("receive", "получил(а)")
            )
            await state.set_state(UserFlow.waiting_for_order_receive)
        elif current_state == UserFlow.waiting_for_feedback:
            # ✅ Следующий вопрос
            await callback.message.edit_text(
                f"💬 Вы оставили отзыв на {nm_id}?", 
                reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
            )
            await state.set_state(UserFlow.waiting_for_feedback)
        # current_state == UserFlow.waiting_for_shk:
        else:
            # ✅ Следующий вопрос
            await callback.message.edit_text(
                f"✂️ ШК разрезали на {nm_id}?", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
            )
            await state.set_state(UserFlow.waiting_for_shk)
    else:
        try:
            await callback.message.edit_text("❌ Фото заказа не принято. Попробуйте прислать корректное фото.")
        except:
            await callback.message.edit_text("Пришлите корректное фото заказа.")

    await callback.answer()

# ==== Обработка кнопок Да/Нет для фото ШК ====
@router.callback_query(F.data.startswith("photo_shk_"))
async def handle_photo_shk(
    callback: CallbackQuery, 
    state: FSMContext,
    CHANNEL_USERNAME: str,
    nm_id: str
):
    answer = "yes" if callback.data.endswith("yes") else "no"
    username = callback.from_user.username or "без username"

    if answer == "yes":
        await callback.message.edit_text("✅ Фото разрезанного ШК принято!")
        await state.update_data(photo_type="other_type")
        # теперь ждём фото ШК
        current_state = await state.get_state() 
        if current_state == UserFlow.waiting_for_agreement:
            await callback.message.answer(
                "Согласны на условия?",
                reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
            )
            await state.set_state(UserFlow.waiting_for_agreement)
        elif current_state == UserFlow.waiting_for_subcription_to_channel:
            # Не подписан
            await callback.message.edit_text(
                "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
            )
            await state.set_state(UserFlow.waiting_for_subcription_to_channel)
        elif current_state == UserFlow.waiting_for_order:
            # 👉 Начинаем пошаговый диалог
            await callback.message.edit_text(
                f"📦 Вы заказали товар {nm_id}?", 
                reply_markup=get_yes_no_keyboard("order", "заказал(а)")
            )
            await state.set_state(UserFlow.waiting_for_order)
        elif current_state == UserFlow.waiting_for_order_receive:
            await callback.message.edit_text(
                f"📬 Вы получили товар {nm_id}?", 
                reply_markup=get_yes_no_keyboard("receive", "получил(а)")
            )
            await state.set_state(UserFlow.waiting_for_order_receive)
        elif current_state == UserFlow.waiting_for_feedback:
            # ✅ Следующий вопрос
            await callback.message.edit_text(
                f"💬 Вы оставили отзыв на {nm_id}?", 
                reply_markup=get_yes_no_keyboard("feedback", "оставил(а)")
            )
            await state.set_state(UserFlow.waiting_for_feedback)
        # current_state == UserFlow.waiting_for_shk:
        else:
            # ✅ Следующий вопрос
            await callback.message.edit_text(
                f"✂️ ШК разрезали на {nm_id}?", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
            )
            await state.set_state(UserFlow.waiting_for_shk)
    else:
        try:
            await callback.message.edit_text("❌ Фото ШК не принято. Попробуйте прислать корректное фото.")
        except:
            await callback.message.edit_text("Пришлите корректное фото разрезанных ШК.")

    await callback.answer()
