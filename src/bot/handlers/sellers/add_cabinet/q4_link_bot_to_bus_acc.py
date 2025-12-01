import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ReplyKeyboardRemove,
    FSInputFile,
    InputMediaPhoto,
    Message,
    CallbackQuery,
)

from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.core.config import constants, settings

from .router import router

@router.callback_query(
    F.data.startswith("link_bot_") , 
    StateFilter(SellerStates.waiting_for_link_bot_to_bus_acc)
)  
async def callback_brand_name(
    callback: CallbackQuery,
    state: FSMContext
):
    await callback.answer()
    if callback.data == "link_bot_yes":
        seller_data = await state.get_data() 
        message_id_to_delete = seller_data["message_id_to_delete"]
        await callback.bot.delete_message(
            chat_id=callback.message.chat.id,
            message_id=message_id_to_delete
        )
        del seller_data['message_id_to_delete']
        await state.set_data(seller_data)
        await callback.message.answer("✅ Отлично!")
        await callback.message.answer(
            "Теперь давайте добавим артикул для раздачи и его фото\n\n"
            "Отправьте *артикул* товара на ВБ, *одно число*",
            parse_mode="MarkdownV2",
        )
        await state.set_state(SellerStates.waiting_for_nm_id)
    else:
        text = "Нужно связать бота и бизнес-аккаунт в телеграме, пожалуйста, сделайте то, что написано выше"
        await callback.message.answer(
            text = StringConverter.escape_markdown_v2(text),
            reply_markup=get_yes_no_keyboard(
                callback_prefix="link_bot",  # префикс оставляем, чтобы не ломать остальную логику
                statement="связал(а)",
            )
        )
        await state.set_state(SellerStates.waiting_for_link_bot_to_bus_acc)

@router.message(StateFilter(SellerStates.waiting_for_link_bot_to_bus_acc))
async def waiting_for_tap_to_keyboard_bus_acc(message: Message):
    await message.answer("Пожалуйста, нажмите на кнопку выше.")


      