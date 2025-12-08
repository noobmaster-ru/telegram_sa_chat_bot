import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.app.bot.keyboards.reply import kb_skip_result_json

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
        text = (
            "✅ Отлично!Теперь мне нужен файл *result.zip*\n\n(Если у вас новый аккаунт, и нет старых переписок с покупателями, тогда нажмите на кнопку *Пропустить result.json* ниже)"
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
        