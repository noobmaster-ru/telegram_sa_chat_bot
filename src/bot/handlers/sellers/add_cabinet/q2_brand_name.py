import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery

from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.string_converter_class import StringConverter
from src.core.config import constants, settings

from .router import router

@router.message(StateFilter(SellerStates.waiting_for_brand_name))
async def handle_brand_name(
    message: Message,
    state: FSMContext,
):   
    brand_name = message.text if message.text else "-"
    await state.update_data(
        brand_name=brand_name
    )
    msg = await message.answer(
        f"Это название вашего бренда *{brand_name}* ?",
        reply_markup=get_yes_no_keyboard(
            callback_prefix="brand_name",
            statement="название бренда"
        ),
        parse_mode="MarkdownV2"
    )
    await state.update_data(
        message_id_to_delete=msg.message_id
    )
    await state.set_state(SellerStates.waiting_for_tap_to_keyboard_brand_name)

@router.callback_query(F.data.startswith("brand_name_") , StateFilter(SellerStates.waiting_for_tap_to_keyboard_brand_name))  
async def callback_brand_name(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()
    seller_data = await state.get_data() 
    message_id_to_delete = seller_data["message_id_to_delete"]
    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=message_id_to_delete
    )
    del seller_data['message_id_to_delete']
    await state.set_data(seller_data)
    if callback.data == "brand_name_yes":
        await callback.message.answer("Теперь необходимо добавить в таблице в редакторы наш сервисный аккаунт Google.")
        INSTRUCTION_PHOTOS_DIR = constants.INSTRUCTION_PHOTOS_DIR
        photo_path1 = INSTRUCTION_PHOTOS_DIR + "1_access_settings.png"
        photo_path2 = INSTRUCTION_PHOTOS_DIR + "2_search_bar.png"
        photo_path3 = INSTRUCTION_PHOTOS_DIR + "3_access_axiomai_editor.png"
        photo_path4 = INSTRUCTION_PHOTOS_DIR + "4_axiomai_service_account.png"

        caption_text = (
            f"Теперь *внимательно!*:\n\n"
            f"1. Откройте свою таблицу\n"
            f"2. В правом верхнем углу откройте настройки доступа *(фото1)*\n"
            f"3. В поисковой строке вбейте вот этот email *(фото2)*:\n\n*{settings.SERVICE_ACCOUNT_AXIOMAI}*\n\n"
            f"4. Дайте доступ *Редактор* этому сервисному аккаунту Google *(фото3)*\n\n"
            f"Как сделаете, у вас должно получиться вот так, как на *(фото4)*"
        )
        safe_caption = StringConverter.escape_markdown_v2(caption_text) 
        media_group = [
            InputMediaPhoto(
                media=FSInputFile(photo_path1),
                caption=safe_caption,
                parse_mode="MarkdownV2"
            ),
            InputMediaPhoto(media=FSInputFile(photo_path2)), 
            InputMediaPhoto(media=FSInputFile(photo_path3)),
            InputMediaPhoto(media=FSInputFile(photo_path4)),
        ]
        # Отправляем медиагруппу
        await callback.bot.send_media_group(
            chat_id=callback.message.chat.id,
            media=media_group
        )
        msg = await callback.message.answer(
            f"Дали доступ *Редактор* нашему cервисному аккаунту Google?",
            reply_markup=get_yes_no_keyboard(
                callback_prefix="service_account",
                statement="дал"
            ),
            parse_mode="MarkdownV2"
        )
        await state.update_data(
            message_id_to_delete=msg.message_id
        )
        await state.set_state(SellerStates.add_cabinet_to_db)
    else:
        await callback.message.answer("Хорошо, отправьте тогда название бренда ещё раз")
        await state.set_state(SellerStates.waiting_for_brand_name)

@router.message(StateFilter(SellerStates.waiting_for_tap_to_keyboard_brand_name))
async def waiting_for_tap_to_keyboard_brand_name(message: Message):
    await message.answer("Пожалуйста, нажмите на кнопку выше.")

@router.message(StateFilter(SellerStates.waiting_for_brand_name))
async def waiting_for_brand_name(message: Message):
    await message.answer("Пожалуйста, пришлите название вашего бренда")

      