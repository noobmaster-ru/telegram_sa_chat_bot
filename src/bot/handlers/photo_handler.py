import asyncio
import base64
import filetype
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage

from src.bot.states.user_flow import UserFlow
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass
from src.bot.utils.last_activity import update_last_activity


router = Router()

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# ловим любой текст в состояних waiting_for_photo_order, waiting_for_photo_feedback , waiting_for_photo_shk и просим отправить фото!
@router.business_message(F.text, StateFilter(UserFlow.waiting_for_photo_order, UserFlow.waiting_for_photo_feedback, UserFlow.waiting_for_photo_shk))
async def handle_photo(message: Message, state: FSMContext):
    await update_last_activity(state)
    current_state = await state.get_state() 
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = message.business_connection_id
    )
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
    await update_last_activity(state)
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    # === 1. Проверяем, не отправил ли пользователь альбом(несколько фоток) ===
    if message.media_group_id is not None:
        user_data = await state.get_data()
        last_media_group = user_data.get("last_media_group_id")
        
        # если этот альбом уже обрабатывали — выходим
        if last_media_group == message.media_group_id:
            return
        
        # иначе сохраняем ID альбома и показываем сообщение
        await state.update_data(last_media_group_id=message.media_group_id)
        photo_type = user_data.get("photo_type", "order") 
        
        if photo_type == "order":
            await message.answer("Пожалуйста, отправьте только один скриншот: скриншот заказа товара.")
            return
        elif photo_type == "feedback":
            await message.answer("Пожалуйста, отправьте только один скриншот: скриншот отзыва товара.")
            return
        elif photo_type == "shk":
            await message.answer("Пожалуйста, отправьте только одну фотографию: фотографию разрезанных этикеток товара.")
            return
        else:
            await message.answer("Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, напишите ваш вопрос текстом.")
            return

    # === 2. Извлекаем данные из FSM ===
    user_data = await state.get_data()
    telegram_id = message.from_user.id
    photo_type = user_data.get("photo_type", "order")  # по умолчанию ждём фото заказа
    nm_id = user_data.get("nm_id")
    nm_id_name = user_data.get("nm_id_name")
    
    # === 3. Получаем фото ===
    photo = message.photo[-1]  # лучшее качество
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    user_bytes = file_bytes.read()
    # 🔹 Конвертируем байты в base64-строку
    base64_image_user = base64.b64encode(user_bytes).decode("utf-8")
    reference_image_extension = filetype.guess(user_bytes).extension
    user_image_url  = f"data:image/{reference_image_extension};base64,{base64_image_user}"

    # обновляем время последнего сообщения юзера
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )
    
    # Читаем байты изображения эталона
    # 4. Загружаем эталонное изображение (например, из файла)
    reference_path = Path(__file__).resolve().parent.parent.parent / "resources" / "flashlight.png"
    reference_image_extension = filetype.guess(reference_path).extension
    base64_image_ref = encode_image(reference_path)
    ref_image_url = f"data:image/{reference_image_extension};base64,{base64_image_ref}"
    
    if photo_type == "order":
        # отправляем в OpenAI для классификации
        await state.set_state("generating")
        model_response = await client_gpt_5.classify_photo_order(
            ref_image_url=ref_image_url,
            user_image_url=user_image_url,
            nm_id=nm_id,
            nm_id_name=nm_id_name
        )

        await spreadsheet.update_buyer_button_and_time(
            telegram_id=telegram_id,
            button_name="photo_order",
            value=model_response,
            is_tap_to_keyboard=False
        )
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING,
            business_connection_id = message.business_connection_id
        )
        await asyncio.sleep(3)
        if model_response == "Да":
            # теперь ждём скрин отзыва
            await state.update_data(photo_type="feedback")
            await message.answer(
                text=f"✅ Скриншот заказа принят\\!",
                parse_mode="MarkdownV2"
            )
            # записали фотку заказа - теперь идем дальше по сценарию - спрашиваем получили ли заказ
            await message.answer(
                f"📬 Вы получили товар [{nm_id}](https://www\\.wildberries\\.ru/catalog/{nm_id}/detail\\.aspx\\?targetUrl=SP)?", 
                reply_markup=get_yes_no_keyboard("receive", "получил(а)"),
                parse_mode="MarkdownV2"
            )
            await state.set_state(UserFlow.waiting_for_order_receive)
        else:
            await state.set_state(UserFlow.waiting_for_photo_order)
            await message.answer("❌ Фото заказа не принято. Попробуйте прислать корректное фото заказа.")

    elif photo_type == "feedback":
        
        # отправляем в OpenAI для классификации
        await state.set_state("generating")
        model_response = await client_gpt_5.classify_photo_feedback(
            ref_image_url=ref_image_url,
            user_image_url=user_image_url,
            nm_id=nm_id,
            nm_id_name=nm_id_name
        )

        await spreadsheet.update_buyer_button_and_time(
            telegram_id=telegram_id,
            button_name="photo_feedback",
            value=model_response,
            is_tap_to_keyboard=False
        )
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING,
            business_connection_id = message.business_connection_id
        )
        await asyncio.sleep(3)
        if model_response == "Да":
            # теперь ждём скрин отзыва
            await state.update_data(photo_type="shk")
            # отвечаем пользователю
            await message.answer(
                text=f"✅ Скриншот отзыва принят\\!",
                parse_mode="MarkdownV2"
            )
            #  Следующий вопрос - разрезали ли ШК
            await message.answer(
                f"✂️ ШК разрезали на [{nm_id}](https://www\\.wildberries\\.ru/catalog/{nm_id}/detail\\.aspx\\?targetUrl=SP)?", 
                reply_markup=get_yes_no_keyboard("shk", "разрезал(а)"),
                parse_mode="MarkdownV2"
            )
            await state.set_state(UserFlow.waiting_for_shk)
        else:
            await state.set_state(UserFlow.waiting_for_photo_feedback)
            await message.answer("❌ Фото отзыва не принято. Попробуйте прислать корректное фото отзыва.")

    elif photo_type == "shk":
        # отправляем в OpenAI для классификации
        await state.set_state("generating")
        model_response = await client_gpt_5.classify_photo_shk(
            ref_image_url=ref_image_url,
            user_image_url=user_image_url,
            nm_id=nm_id,
            nm_id_name=nm_id_name
        )

        await spreadsheet.update_buyer_button_and_time(
            telegram_id=telegram_id,
            button_name="photo_shk",
            value=model_response,
            is_tap_to_keyboard=False
        )
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING,
            business_connection_id = message.business_connection_id
        )
        await asyncio.sleep(3)
        if model_response == "Да":
            # получили все фотки: заказ, отзыв, ШК
            await state.update_data(photo_type="other_type")
            # отвечаем пользователю
            await message.answer(
                text=f"✅ Фото разрезанных этикеток принято\\!",
                parse_mode="MarkdownV2"
            )
            await message.answer("☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо!")
            await message.answer(
                "Отправьте теперь нам, пожалуйста, свои реквизиты в формате:\nНомер карты в формате:\nAAAA BBBB CCCC DDDD\n   *ИЛИ*\nНомер телефона в формате: 8910XXXXXXX\n\nСпасибо",
                parse_mode="MarkdownV2"
            )
            await state.set_state(UserFlow.waiting_for_requisites)
        else:
            await state.set_state(UserFlow.waiting_for_photo_shk)
            await message.answer("❌ Фото разрезанных штрихкодов не принято. Попробуйте прислать корректное фото разрезанных штрихкодов")

    # photo_type == "other_type" ,юзер тупой и продолжает отправлять ненужные фотографии
    else:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING,
            business_connection_id = message.business_connection_id
        )
        await asyncio.sleep(3)
        current_state = await state.get_state() 
        if current_state == UserFlow.waiting_for_requisites:
            await message.answer(
                "☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, теперь отправьте нам свои реквизиты в формате:\nНомер карты в формате: AAAA BBBB CCCC DDDD\n *ИЛИ* \nНомер телефона: 8910XXXXXXX",
                parse_mode="MarkdownV2"
            )
        elif current_state == UserFlow.continue_dialog:
            await message.answer("Вы прислали все фотографии, которые были нам нужны. Спасибо! Пожалуйста, напишите ваш вопрос текстом.")