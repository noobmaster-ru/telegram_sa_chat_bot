import logging
from aiogram import F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove,  Message, CallbackQuery

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.core.config import constants

from .router import router

# SELLER_MENU_TEXT[0] == '⚙️Добавить кабинет'
# @router.message(F.text == constants.SELLER_MENU_TEXT[0], StateFilter(SellerStates.waiting_for_tap_to_menu))
# async def handle_organization_name(
#     message: Message,
#     state: FSMContext
# ):
    # # text = "Введите *ТОЧНОЕ* название вашего магазина/бренда, *который видят покупатели на ВБ(нужно для AI)*:"
    # await message.answer(
    #     text = StringConverter.escape_markdown_v2(text),
    #     reply_markup=ReplyKeyboardRemove(),
    #     parse_mode="MarkdownV2"
    # )
    # await state.set_state(SellerStates.waiting_for_organization_name)


# @router.message(StateFilter(SellerStates.waiting_for_organization_name))
# async def handle_organization_name(
#     message: Message,
#     state: FSMContext,
# ):
#     organization_name = message.text if message.text else "-"
#     await state.update_data(
#         organization_name=organization_name
#     )
#     msg_text = f"Это название вашего магазина?:\n\n *{organization_name}*"
#     msg = await message.answer(
#         text=StringConverter.escape_markdown_v2(msg_text),
#         reply_markup=get_yes_no_keyboard(
#             callback_prefix="organization_name",
#             statement="название кабинета"
#         ),
#         parse_mode="MarkdownV2"
#     )
#     await state.update_data(
#         message_id_to_delete=msg.message_id
#     )
#     await state.set_state(SellerStates.waiting_for_tap_to_keyboard_org_name)

@router.message(F.text == constants.SELLER_MENU_TEXT[0], StateFilter(SellerStates.waiting_for_tap_to_menu))
async def handle_add_cabinet(
    message: Message,
    state: FSMContext
):
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
    text =  f'Сделайте себе копию этой таблицы\n\n {constants.GOOGLE_SHEETS_TEMPLATE_URL}\n\nвставьте в ячейку B2 ссылку на ваш артикул, подождите пока подгрузятся данные c сайта ВБ и пришлите мне *ссылку на таблицу*'
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(SellerStates.waiting_for_new_google_sheets_url)

# @router.callback_query(F.data.startswith("organization_name_") , StateFilter(SellerStates.waiting_for_tap_to_keyboard_org_name))
# async def callback_org_name(
#     callback: CallbackQuery,
#     state: FSMContext
# ):
#     await callback.answer()
#     seller_data = await state.get_data() 
#     message_id_to_delete = seller_data["message_id_to_delete"]
#     await callback.bot.delete_message(
#         chat_id=callback.message.chat.id,
#         message_id=message_id_to_delete
#     )
#     del seller_data['message_id_to_delete']
#     await state.set_data(seller_data)
#     if callback.data == "organization_name_yes": 
#         text =  f'Сделайте себе копию этой таблицы\n\n {constants.GOOGLE_SHEETS_TEMPLATE_URL}\n\n и пришлите мне ссылку на неё'
#         await callback.message.answer(
#             text=StringConverter.escape_markdown_v2(text),
#             parse_mode="MarkdownV2"
#         )
#         await state.set_state(SellerStates.waiting_for_new_google_sheets_url)
#     else:
#         text = "Хорошо, отправьте тогда название магазина ещё раз"
#         await callback.message.answer(
#             text=StringConverter.escape_markdown_v2(text),
#             parse_mode="MarkdownV2"
#         )
#         await state.set_state(SellerStates.waiting_for_organization_name)


# @router.message(StateFilter(SellerStates.waiting_for_tap_to_keyboard_org_name))
# async def waiting_for_tap_to_keyboard_gs(message: Message):
#     text = "Пожалуйста, нажмите на кнопку выше."
#     await message.answer(
#         text=StringConverter.escape_markdown_v2(text),
#         parse_mode="MarkdownV2"
#     )
