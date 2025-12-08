import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    FSInputFile,
    InputMediaPhoto,
    Message,
    CallbackQuery,
)

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter

from src.core.config import settings, constants

from .router import router


@router.message(
    F.text.startswith('http'), 
    StateFilter(SellerStates.waiting_for_new_google_sheets_url)
)
async def handle_gs_url(
    message: Message,
    state: FSMContext,
):
    google_sheets_url = message.text if message.text else "-"
    if google_sheets_url == constants.GOOGLE_SHEETS_TEMPLATE_URL:
        text = f"Пожалуйста, отправьте ссылку на *СВОЮ* таблицу!"
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return 
    await state.update_data(
        google_sheets_url=google_sheets_url
    )
    text = f"Это ваша ссылка на таблицу?:\n\n {google_sheets_url}"
    msg = await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=get_yes_no_keyboard(
            callback_prefix="gs_url",
            statement="cсылка на google sheets"
        ),
        parse_mode="MarkdownV2"
    )
    await state.update_data(
        message_id_to_delete=msg.message_id
    )
    await state.set_state(SellerStates.waiting_for_tap_to_keyboard_gs)


@router.callback_query(F.data.startswith("gs_url_") , StateFilter(SellerStates.waiting_for_tap_to_keyboard_gs))
async def callback_gs_url(
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
    if callback.data == "gs_url_yes":  
        text = "Теперь необходимо добавить в таблице в редакторы наш сервисный аккаунт Google."
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        INSTRUCTION_PHOTOS_DIR = constants.INSTRUCTION_PHOTOS_DIR
        photo_path1 = INSTRUCTION_PHOTOS_DIR + "1_access_settings.png"
        photo_path2 = INSTRUCTION_PHOTOS_DIR + "2_search_bar.png"
        photo_path3 = INSTRUCTION_PHOTOS_DIR + "3_access_axiomai_editor.png"
        photo_path4 = INSTRUCTION_PHOTOS_DIR + "4_axiomai_service_account.png"

        caption_text = (
            f"Теперь *внимательно!*:\n\n"
            f"1. Откройте свою таблицу\n"
            f"2. В правом верхнем углу откройте настройки доступа *(фото1)*\n"
            f"3. В поисковой строке вбейте вот этот email *(фото2)*:\n\n*{settings.SERVICE_ACCOUNT_AXIOMAI_EMAIL}*\n\n"
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
        text = f"Дали доступ *Редактор* нашему cервисному аккаунту Google?"
        msg = await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
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
        text = "Хорошо, отправьте тогда ссылку ещё раз"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_new_google_sheets_url)


@router.message(StateFilter(SellerStates.waiting_for_new_google_sheets_url))
async def waiting_for_gs_url(message: Message):
    text = "Пожалуйста, пришлите ссылку на гугл-таблицу(без других слов)"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )


@router.message(StateFilter(SellerStates.waiting_for_tap_to_keyboard_gs))
async def waiting_for_tap_to_keyboard_gs(message: Message):
    text = "Пожалуйста, нажмите на кнопку выше."
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )
