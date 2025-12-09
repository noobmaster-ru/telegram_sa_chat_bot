import logging
from redis.asyncio import Redis

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, Message, CallbackQuery

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.reply import kb_skip_result_json, kb_buy_leads
from src.tools.string_converter_class import StringConverter
from src.tools.parse_telegram_ids_from_result_json import parse_zipped_result_json

from src.core.config import constants

from .router import router


@router.message(F.document , StateFilter(SellerStates.waiting_result_json))
async def waiting_for_result_json(
    message: Message,
    state: FSMContext,
    redis: Redis
):
    # 1. Проверяем расширение (не строго обязательно, но удобно)
    file_name = message.document.file_name or ""
    if not file_name.lower().endswith(".zip"):
        text = (
            "Файл result.json слишком большой (больше 50МБ)\n"
            "Пожалуйста, cожмите файл result.json в .zip и отправьте мне этот архив😊"
        )
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2",
        )
        return
    text = "Считываю id написавших клиентов ..."
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
        reply_markup=ReplyKeyboardRemove()
    )
    # 2. Скачиваем файл целиком в память
    tg_file = await message.bot.get_file(message.document.file_id)
    file_obj = await message.bot.download_file(tg_file.file_path)
    file_bytes = file_obj.read()  # <- ВАЖНО: превращаем в bytes

    try:
        user_ids = parse_zipped_result_json(file_bytes)
    except ValueError as e:
        # ошибки типа "не ZIP", "нет JSON", "битый JSON" и т.п.
        await message.answer(
            text=StringConverter.escape_markdown_v2(f"Ошибка при разборе файла: {e}"),
            parse_mode="MarkdownV2",
        )
        return
    
    # 3. Достаём данные из FSM
    seller_data = await state.get_data() 
    business_connection_id = seller_data.get("business_connection_id")
    
    redis_key = (
        f"{constants.REDIS_KEY_OLD_USERS}:{business_connection_id}:old_users_telegram_ids"
    )
    await redis.sadd(redis_key, *user_ids)


    msg_text = f"Импортировано {len(user_ids)} старых клиентов.\n"
    await message.answer(
        text=StringConverter.escape_markdown_v2(msg_text),
        parse_mode="MarkdownV2"
    )

    # text = (
    #     "Теперь давайте добавим артикул для раздачи и его фото\n\n"
    #     "Отправьте *артикул* товара на ВБ, *одно число*"
    # )
    # await message.answer(
    #     text=StringConverter.escape_markdown_v2(text),
    #     parse_mode="MarkdownV2",
    #     reply_markup=ReplyKeyboardRemove()
    # )
    # await state.set_state(SellerStates.waiting_for_nm_id)
    text=f"Теперь необходимо купить лиды на кабинет, нажмите на клавиатуре {constants.SELLER_MENU_TEXT[1]}"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=kb_buy_leads,
        parse_mode="MarkdownV2",
    )
    await state.set_state(SellerStates.waiting_for_leads)


@router.callback_query(
    F.text == constants.SELLER_MENU_TEXT[5], # пропустить result.json
    StateFilter(SellerStates.waiting_result_json)
)  
async def callback_skip_result_json(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()
    seller_data = await state.get_data() 
    try:
        message_id_to_delete = seller_data["message_id_to_delete"]
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=message_id_to_delete
        )
        del seller_data['message_id_to_delete']
        await state.set_data(seller_data)
    except:
        pass

    text = (
        "Теперь давайте добавим артикул для раздачи и его фото\n\n"
        "Отправьте *артикул* товара на ВБ, *одно число*"
    )
    await callback.message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(SellerStates.waiting_for_nm_id)



@router.message(StateFilter(SellerStates.waiting_result_json))
async def handle_unexpect_text_resul_json(
    message: Message,
    state: FSMContext
):
    seller_data = await state.get_data() 
    message_id_to_delete = seller_data["message_id_to_delete"]
    await message.bot.delete_message(
        chat_id=message.chat.id,
        message_id=message_id_to_delete
    )
    del seller_data['message_id_to_delete']
    await state.set_data(seller_data)
    text = "Отправьте, пожалуйста, файл *result.json*\n\n\n(Если у вас новый аккаунт, и нет старых переписок с покупателями, тогда нажмите на кнопку *Пропустить result.json* ниже)"
    msg = await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
        reply_markup=kb_skip_result_json
    )
    await state.update_data(
        message_id_to_delete=msg.message_id
    )
