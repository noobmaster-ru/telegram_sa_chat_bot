import logging
from redis.asyncio import Redis

from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

@router.message(StateFilter(SellerStates.waiting_for_business_account_id))
async def waiting_for_tap_to_keyboard_bus_acc(
    message: Message,
    state: FSMContext
):
    bus_acc_id = message.text if message.text else "-"
    await state.update_data(
        bus_acc_id=bus_acc_id
    )
    msg_text = f"Получен ID:\n\n *{bus_acc_id}*\n\nОн совпадает с тем, что вам сказал {constants.BOT_TO_GET_ID}?"
    msg = await message.answer(
        text=StringConverter.escape_markdown_v2(msg_text),
        reply_markup=get_yes_no_keyboard(
            callback_prefix="bus_acc_id",
            statement="совпадает"
        ),
        parse_mode="MarkdownV2"
    )
    await state.update_data(
        message_id_to_delete=msg.message_id
    )
    await state.set_state(SellerStates.waiting_for_tap_to_keyboard_bus_acc_id)


@router.callback_query(
    F.data.startswith("bus_acc_id_") , 
    StateFilter(SellerStates.waiting_for_tap_to_keyboard_bus_acc_id)
)  
async def callback_brand_name(
    callback: CallbackQuery,
    state: FSMContext,
    redis: Redis
):
    await callback.answer()
    seller_data = await state.get_data() 
    message_id_to_delete = seller_data["message_id_to_delete"]
    bus_acc_id = seller_data["bus_acc_id"]
    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=message_id_to_delete
    )
    del seller_data['message_id_to_delete']
    await state.set_data(seller_data)
    
    if callback.data == "bus_acc_id_yes":
        text = "✅ Отлично! теперь бот точно привязан к вашему бизнес-аккаунту🔥"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await redis.sadd(constants.REDIS_KEY_BUSINESS_ACCOUNTS_IDS, bus_acc_id)
        
        # text = (
        #     "Теперь давайте добавим артикул для раздачи и его фото\n\n"
        #     "Отправьте *артикул* товара на ВБ, *одно число*"
        # )
        # await callback.message.answer(
        #     text=StringConverter.escape_markdown_v2(text),
        #     parse_mode="MarkdownV2"
        # )
        # await state.set_state(SellerStates.waiting_for_nm_id)
                
        text = (
            "Теперь мне нужен *business_connection_id* , который вам отправил ваш бизнес-аккаунт"
        )
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_business_connection_id)
    else:
        text = f"Мне нужен ID вашего бизнесс-аккаунта, пожалуйста, перешлите сообщение вашего бизнесс-аккаунта  боту {constants.BOT_TO_GET_ID} и пришлите мне его ID"
        await callback.message.answer(
            text = StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_business_account_id)


@router.message(StateFilter(SellerStates.waiting_for_tap_to_keyboard_bus_acc_id))
async def handle_unexpect_text_bus_acc(message: Message):
    text = "Пожалуйста, нажмите на кнопку выше"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )

