from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import logging
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.google_sheets_class import GoogleSheetClass
from src.bot.states.user_flow import UserFlow
from src.services.open_ai_requests_class import OpenAiRequestClass

from aiogram.filters import StateFilter

router = Router()


# ловим любой текст в состояних waiting_for_photo_order, waiting_for_photo_feedback , waiting_for_photo_shk и просим отправить фото!
@router.business_message(F.text, StateFilter(UserFlow.waiting_for_photo_order, UserFlow.waiting_for_photo_feedback, UserFlow.waiting_for_photo_shk))
async def handle_photo(message: Message, state: FSMContext):
    current_state = await state.get_state() 
    if current_state == UserFlow.waiting_for_photo_order:
        await message.answer("Пришлите, пожалуйста, скриншот заказа.")
    elif current_state == UserFlow.waiting_for_photo_feedback:
        await message.answer("Пришлите, пожалуйста, скриншот отзыва на 5 звёзд.")
    # current_state == UserFlow.waiting_for_photo_shk:
    else:
        await message.answer("Пришлите, пожалуйста, фотографию разрезанных этикеток.")


# ==== Получение фото от пользователя ==== 
@router.business_message(F.photo, StateFilter(UserFlow.waiting_for_photo_order, UserFlow.waiting_for_photo_feedback, UserFlow.waiting_for_photo_shk))
async def handle_photo(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass
):
    user_data = await state.get_data()
    telegram_id = message.from_user.id
    photo_type = user_data.get("photo_type", "order")  # по умолчанию ждём фото заказа
    nm_id = user_data.get("nm_id")
    
    # 1. получаем файл с фото от Telegram
    photo = message.photo[-1]  # лучшее качество
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    user_bytes = file_bytes.read()
    
    # обновляем время последнего сообщения юзера
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    
    # Читаем байты изображения эталона
    # 2. Загружаем эталонное изображение (например, из файла)
    reference_path = Path(__file__).resolve().parent.parent.parent / "resources" / "flashlight.png"
    reference_bytes = reference_path.read_bytes()
    if photo_type == "order":

        # отправляем в OpenAI для классификации
        model_response = await client_gpt_5.classify_photo_order(
            reference_bytes=reference_bytes,
            user_bytes=user_bytes,
            nm_id=nm_id
        )
        # отвечаем пользователю
        await message.answer(
            text=f"Ответ модели: *{model_response}*, запишем в таблицу",
            parse_mode="MarkdownV2"
        )
        await spreadsheet.update_buyer_button_and_time(
            telegram_id=telegram_id,
            button_name="photo_order",
            value=model_response,
            is_tap_to_keyboard=False
        )
        if model_response == "Да":
            # теперь ждём скрин отзыва
            await state.update_data(photo_type="feedback")
            
            # записали фотку заказа - теперь идем дальше по сценарию - спрашиваем получили ли заказ
            await message.answer(
                f"📬 Вы получили товар {nm_id}?", 
                reply_markup=get_yes_no_keyboard("receive", "получил(а)")
            )
            await state.set_state(UserFlow.waiting_for_order_receive)
        else:
            await message.answer("❌ Фото заказа не принято. Попробуйте прислать корректное фото заказа.")

        # await message.answer(
        #     "📸 Это скрин заказа?",
        #     reply_markup=get_yes_no_keyboard(
        #         callback_prefix="photo_order_", 
        #         statement="скрин заказа"
        #     )
        # )
    elif photo_type == "feedback":
        
        # отправляем в OpenAI для классификации
        model_response = await client_gpt_5.classify_photo_feedback(
            reference_bytes=reference_bytes,
            user_bytes=user_bytes,
            nm_id=nm_id
        )
        # отвечаем пользователю
        await message.answer(
            text=f"Ответ модели: *{model_response}*, запишем в таблицу",
            parse_mode="MarkdownV2"
        )
        await spreadsheet.update_buyer_button_and_time(
            telegram_id=telegram_id,
            button_name="photo_feedback",
            value=model_response,
            is_tap_to_keyboard=False
        )
        if model_response == "Да":
            # теперь ждём скрин отзыва
            await state.update_data(photo_type="shk")
            
            #  Следующий вопрос - разрезали ли ШК
            await message.answer(
                f"✂️ ШК разрезали на {nm_id}?", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
            )
            await state.set_state(UserFlow.waiting_for_shk)
        else:
            await message.answer("❌ Фото отзыва не принято. Попробуйте прислать корректное фото отзыва.")

        # спрашиваем подтверждение, что это фото отзыва
        # await message.answer(
        #     "📸 Это скрин отзыва?",
        #     reply_markup=get_yes_no_keyboard(
        #         callback_prefix="photo_feedback_",
        #         statement="скрин отзыва")
        # )
    elif photo_type == "shk":
        # отправляем в OpenAI для классификации
        model_response = await client_gpt_5.classify_photo_shk(
            reference_bytes=reference_bytes,
            user_bytes=user_bytes,
            nm_id=nm_id
        )
        # отвечаем пользователю
        await message.answer(
            text=f"Ответ модели: *{model_response}*, запишем в таблицу",
            parse_mode="MarkdownV2"
        )
        await spreadsheet.update_buyer_button_and_time(
            telegram_id=telegram_id,
            button_name="photo_shk",
            value=model_response,
            is_tap_to_keyboard=False
        )
        if model_response == "Да":
            # получили все фотки: заказ, отзыв, ШК
            await state.update_data(photo_type="other_type")

            await message.answer("☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо!")
            await message.answer(
                "Отправьте теперь нам, пожалуйста, свои реквизиты в формате:\n- Номер карты: AAAA BBBB CCCC DDDD\n  *ИЛИ*\n- Номер телефона: 8910XXXXXXX\n\nСпасибо",
                parse_mode="MarkdownV2"
            )
            await state.set_state(UserFlow.waiting_for_requisites)
        else:
            await message.answer("❌ Фото разрезанных штрихкодов не принято. Попробуйте прислать корректное фото разрезанных штрихкодов")

        # спрашиваем подтверждение, что это фото разрезанного ШК
        # await message.answer(
        #     "📸 Это фотография разрезанных штрихкодов?",
        #     reply_markup=get_yes_no_keyboard(
        #         callback_prefix="photo_shk_",
        #         statement="скрин разрезанного ШК")
        # )
    # photo_type == "other_type" ,юзер тупой и продолжает отправлять ненужные фотографии
    else:
        current_state = await state.get_state() 
        if current_state == UserFlow.waiting_for_requisites:
            await message.answer(
                "☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, теперь отправьте нам свои реквизиты в формате:\n- Номер карты: AAAA BBBB CCCC DDDD\n *ИЛИ* \n- Номер телефона: 8910XXXXXXX",
                parse_mode="MarkdownV2"
            )
        elif current_state == UserFlow.continue_dialog:
            await message.answer("Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, напишите ваш вопрос текстом.")

# # ==== Обработка кнопок Да/Нет для фото заказа ====
# @router.callback_query(F.data.startswith("photo_order_"))
# async def handle_photo_order(
#     callback: CallbackQuery,
#     state: FSMContext,
#     spreadsheet: GoogleSheetClass
# ):
#     answer = "Да" if callback.data.endswith("yes") else "Нет"
#     telegram_id = callback.from_user.id
#     data = await state.get_data()
#     nm_id = data.get("nm_id")

    
#     await spreadsheet.update_buyer_button_and_time(
#         telegram_id=telegram_id,
#         button_name="photo_order",
#         value=answer,
#         is_tap_to_keyboard=True
#     )
    
#     if answer == "Да":
#         await callback.message.edit_text("✅ Скрин заказа принят!")

#         # теперь ждём скрин отзыва
#         await state.update_data(photo_type="feedback")
        
#         # записали фотку заказа - теперь идем дальше по сценарию - спрашиваем получили ли заказ
#         await callback.message.edit_text(
#             f"📬 Вы получили товар {nm_id}?", 
#             reply_markup=get_yes_no_keyboard("receive", "получил(а)")
#         )
#         await state.set_state(UserFlow.waiting_for_order_receive)
  
#     else:
#         try:
#             await callback.message.edit_text("❌ Фото заказа не принято. Попробуйте прислать корректное фото.")
#         except:
#             await callback.message.edit_text("Пришлите корректное фото заказа.")

#     await callback.answer()
    
# # ==== Обработка кнопок Да/Нет для скрина отзыва ====
# @router.callback_query(F.data.startswith("photo_feedback_"))
# async def handle_photo_feedback(
#     callback: CallbackQuery, 
#     state: FSMContext,
#     CHANNEL_USERNAME: str,
#     spreadsheet: GoogleSheetClass
# ):
#     answer = "Да" if callback.data.endswith("yes") else "Нет"
#     telegram_id = callback.from_user.id
#     data = await state.get_data()
#     nm_id = data.get("nm_id")

    
#     await spreadsheet.update_buyer_button_and_time(
#         telegram_id=telegram_id,
#         button_name="photo_feedback",
#         value=answer,
#         is_tap_to_keyboard=True
#     )
    
#     if answer == "Да":
#         await callback.message.edit_text("✅ Скрин отзыва принят!")
#         # теперь ждём фото ШК
#         await state.update_data(photo_type="shk")
    

#         #  Следующий вопрос - разрезали ли ШК
#         await callback.message.edit_text(
#             f"✂️ ШК разрезали на {nm_id}?", 
#             reply_markup=get_yes_no_keyboard("shk", "разрезал(а)")
#         )
#         await state.set_state(UserFlow.waiting_for_shk)
#     else:
#         try:
#             await callback.message.edit_text("❌ Скрин отзыва не принят. Попробуйте прислать корректный скриншот.")
#         except:
#             await callback.message.edit_text("Пришлите корректный скриншот отзыва.")


# # ==== Обработка кнопок Да/Нет для фото ШК ====
# @router.callback_query(F.data.startswith("photo_shk_"))
# async def handle_photo_shk(
#     callback: CallbackQuery, 
#     state: FSMContext,
#     CHANNEL_USERNAME: str,
#     spreadsheet: GoogleSheetClass
# ):
#     answer = "Да" if callback.data.endswith("yes") else "Нет"
#     telegram_id = callback.from_user.id
#     data = await state.get_data()
#     nm_id = data.get("nm_id")

    
#     await spreadsheet.update_buyer_button_and_time(
#         telegram_id=telegram_id,
#         button_name="photo_shk",
#         value=answer,
#         is_tap_to_keyboard=True
#     )
    
#     if answer == "Да":
#         await callback.message.edit_text("✅ Фото разрезанного ШК принято!")
        
#         # получили все фотки: заказ, отзыв, ШК
#         await state.update_data(photo_type="other_type")

#         await callback.message.answer("☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, теперь отправьте нам свои реквизиты в формате:\n- Номер карты: AAAA BBBB CCCC DDDD или\n- Номер телефона: 8910XXXXXXX \n- Название банка: Сбербанк, Т-банк\n-Cумму для оплаты: 550 рублей\nМы свяжемся с вами через некоторое время,спасибо")
#         await state.set_state(UserFlow.waiting_for_requisites)
#     else:
#         try:
#             await callback.message.edit_text("❌ Фото ШК не принято. Попробуйте прислать корректное фото.")
#         except:
#             await callback.message.edit_text("Пришлите корректное фото разрезанных ШК.")
