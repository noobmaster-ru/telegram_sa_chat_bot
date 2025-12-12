import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, 
    CallbackQuery,
    FSInputFile,
    InputMediaPhoto
)

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.app.bot.keyboards.reply import kb_skip_result_json
from src.core.config import constants

from .router import router

@router.message(StateFilter(SellerStates.waiting_for_business_connection_id))
async def handle_business_connection_id(
    message: Message,
    state: FSMContext,
):
    business_connection_id = message.text 
    await state.update_data(
        business_connection_id=business_connection_id
    )
    seller_data = await state.get_data() 

    try:
        message_id_to_delete = seller_data["message_id_to_delete"]
        await message.bot.delete_message(
            chat_id=message.chat.id,
            message_id=message_id_to_delete
        )
        del seller_data['message_id_to_delete']
        await state.set_data(seller_data)
    except:
        pass
    text = (
        f"Получены данные:\n"
        f"business_connection_id: `{business_connection_id}`\n"
        f"Всё верно?"
    )
    msg = await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
        reply_markup=get_yes_no_keyboard(
            callback_prefix="business_connection_id",
            statement='верно'
        )
    )
    await state.update_data(
        message_id_to_delete=msg.message_id
    )
    

@router.callback_query(
    F.data.startswith("business_connection_id") , 
    StateFilter(SellerStates.waiting_for_business_connection_id)
)  
async def callback_business_connection_id(
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
    
    if callback.data == "business_connection_id_yes":
        INSTRUCTION_PHOTOS_DIR = constants.INSTRUCTION_PHOTOS_DIR
        photo_path1 = INSTRUCTION_PHOTOS_DIR + "5_settings.png"
        photo_path2 = INSTRUCTION_PHOTOS_DIR + "6_advanced.png"
        photo_path3 = INSTRUCTION_PHOTOS_DIR + "7_export_telegram_data.png"
        photo_path4 = INSTRUCTION_PHOTOS_DIR + "8_export_settings.png"
        photo_path5 = INSTRUCTION_PHOTOS_DIR + "9_export_settings.png"
        photo_path6 = INSTRUCTION_PHOTOS_DIR + "10_export_settings.png"
        photo_path7 = INSTRUCTION_PHOTOS_DIR + "11_export_settings.png"
        photo_path8 = INSTRUCTION_PHOTOS_DIR + "12_data.png"
        photo_path9 = INSTRUCTION_PHOTOS_DIR + "13_data.png"
        caption_text = (
            f"Теперь *внимательно!*:\n\n"
            f"Чтобы бот не отвечал старым клиентам ,которые уже писали по поводу раздач, мне нужен файл с вашими данными по перепискам.\n"
            f"Его можно получить через десктоп-версию телеграма: https://desktop.telegram.org/ \n\n"
            f"Скачивайте приложение , и следуйте инструкциям на фотографиях:\nsettings --> advanced --> export Telegram data --> установить флажки на нужных ячейках как на фото --> *machine-readable JSON*(очень важно именно *json*) --> Export\n"
            f"Скачивание файла может занять достаточно долгое время, если у вас было много покупателей(минут 10-20), дождитейсь когда файл скачается.\n"
            "Скачается папка DataExport_... , внутри этой папки будет файл result.json , вот он мне и нужен☺️\n\n"
            "(P.S. Если файл result.json по размеру будет больше 50МБ, то его необходимо сжать в .zip и отправить мне этот архив)"
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
            InputMediaPhoto(media=FSInputFile(photo_path5)),
            InputMediaPhoto(media=FSInputFile(photo_path6)),
            InputMediaPhoto(media=FSInputFile(photo_path7)),
            InputMediaPhoto(media=FSInputFile(photo_path8)),
            InputMediaPhoto(media=FSInputFile(photo_path9)),
        ]
        # Отправляем медиагруппу
        await callback.bot.send_media_group(
            chat_id=callback.message.chat.id,
            media=media_group
        )
        text = (
            "Отправьте мне файл *result.json*\n\n"
            "(Если у вас новый аккаунт, и нет старых переписок с покупателями, тогда нажмите на кнопку *Пропустить result.json* ниже)"
        )
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2",
            reply_markup=kb_skip_result_json
        )
        await state.set_state(SellerStates.waiting_result_json)
    else:
        text = f"Хорошо, отправьте заново business_connection_id"
        await callback.message.answer(
            text = StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_business_connection_id)
        