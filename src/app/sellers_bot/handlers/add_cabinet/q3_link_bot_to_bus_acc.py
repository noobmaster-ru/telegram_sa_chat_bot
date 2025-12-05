import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.app.bot.states.seller import SellerStates
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

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
        
        text = "✅ Отлично! бот привязан к вашему бизнес-аккаунту😊🥳"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        
        text = f"Теперь пришлите мне ID , который вам выдал {constants.BOT_TO_GET_ID}"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_business_account_id)
    else:
        text = "Нужно связать бота и бизнес-аккаунт в телеграме, пожалуйста, сделайте то, что написано выше и нажмите на кнопку 'Да,связал'"
        await callback.message.answer(
            text = StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_link_bot_to_bus_acc)

@router.message(StateFilter(SellerStates.waiting_for_link_bot_to_bus_acc))
async def waiting_for_tap_to_keyboard_bus_acc(message: Message):
    text = "Пожалуйста, нажмите на кнопку выше."
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )


      