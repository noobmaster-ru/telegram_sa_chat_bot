import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove,  Message, CallbackQuery

from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.core.config import constants

from .router import router

# SELLER_MENU_TEXT[0] == '⚙️Добавить кабинет'
@router.message(F.text == constants.SELLER_MENU_TEXT[0], StateFilter(SellerStates.waiting_for_tap_to_menu))
async def add_cabinet(
    message: Message,
    state: FSMContext
):
    await message.answer(
        text=f'Сделайте себе копию этой таблицы\n\n {constants.GOOGLE_SHEETS_TEMPLATE_URL}\n\n и пришлите мне ссылку на неё',
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(SellerStates.waiting_for_new_google_sheets_url)
    
@router.message(
    F.text.startswith('http'), 
    StateFilter(SellerStates.waiting_for_new_google_sheets_url)
)
async def handle_gs_url(
    message: Message,
    state: FSMContext,
):
    google_sheets_url = message.text if message.text else "-"
    await state.update_data(
        google_sheets_url=google_sheets_url
    )
    msg = await message.answer(
        f"Это ваша ссылка на таблицу?:\n\n {google_sheets_url}",
        reply_markup=get_yes_no_keyboard(
            callback_prefix="gs_url",
            statement="cсылка на google sheets"
        )
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
        await callback.message.answer(
            "Теперь отправьте название вашего *ИП/OOO* на ВБ",
            parse_mode="MarkdownV2"
        )
        await state.set_state(SellerStates.waiting_for_brand_name)
    else:
        await callback.message.answer("Хорошо, отправьте тогда ссылку ещё раз")
        await state.set_state(SellerStates.waiting_for_new_google_sheets_url)


@router.message(StateFilter(SellerStates.waiting_for_new_google_sheets_url))
async def waiting_for_gs_url(message: Message):
    await message.answer("Пожалуйста, пришлите ссылку на гугл-таблицу(без других слов)")


@router.message(StateFilter(SellerStates.waiting_for_tap_to_keyboard_gs))
async def waiting_for_tap_to_keyboard_gs(message: Message):
    await message.answer("Пожалуйста, нажмите на кнопку выше.")
