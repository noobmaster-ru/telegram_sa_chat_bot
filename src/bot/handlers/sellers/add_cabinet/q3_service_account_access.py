import logging
from pathlib import Path
from aiogram import F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import ReplyKeyboardRemove, FSInputFile, InputMediaPhoto, Message, CallbackQuery

from src.db.models import CabinetORM
from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.services.string_converter_class import StringConverter
from src.core.config import constants, settings

from .router import router
    

@router.callback_query(
    F.data.startswith("service_account"),
    StateFilter(SellerStates.add_cabinet_to_db)
)
async def handle_add_service_account_into_gs(
    callback: CallbackQuery,
    state: FSMContext,
    db_session_factory: async_sessionmaker,
    bot: Bot
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
    if callback.data == "service_account_yes": 
        user_data = await state.get_data()    
        google_sheets_url = user_data["google_sheets_url"]
        user_id = user_data["user_id"]
        brand_name = user_data["brand_name"]
        
        async with db_session_factory() as session:
            new_cabinet = CabinetORM(
                brand_name=brand_name,
                table_link=google_sheets_url,
                user_id=user_id
            )
            session.add(new_cabinet)
            await session.commit()
            
            # session.refresh(new_cabinet) — подтянет cabinet.id
            await session.refresh(new_cabinet)   
            
            # Сохраняем user_id(id in postgresql) в FSM
            await state.update_data(cabinet_id=new_cabinet.id)
        await callback.message.answer("✅Кабинет успешно добавлен!")
        await callback.message.answer(
            "Теперь давайте добавим артикулы для раздачи и количество раздач\n\nОтправьте *артикул* товара на ВБ , *одно число*",
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_nm_id)
    else:
        await callback.message.answer("Пожалуйста, добавьте сервисный аккаунт в гугл-таблицу, без добавления мы не сможем записывать данные в вашу таблицу")
        await callback.message.answer("Вот подробная инструкция")
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
        await bot.send_media_group(
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
    
@router.message(StateFilter(SellerStates.add_cabinet_to_db))
async def waiting_for_tap_to_keyboard_add_cabine_to_db(message: Message):
    await message.answer("Пожалуйста, нажмите на кнопку выше.")

