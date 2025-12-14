# import logging
# from aiogram import F
# from aiogram.filters import  StateFilter
# from aiogram.types import Message,  CallbackQuery
# from aiogram.fsm.context import FSMContext

# from sqlalchemy.ext.asyncio import async_sessionmaker
# from sqlalchemy import select

# from src.app.bot.keyboards.reply import kb_add_cabinet
# from src.app.bot.states.seller import SellerStates
# from src.app.bot.keyboards.inline import get_yes_no_keyboard
# from src.infrastructure.db.models import UserORM
# from src.tools.string_converter_class import StringConverter

# from .router import router


# @router.message(StateFilter(SellerStates.email))
# async def handle_email(
#     message: Message,
#     state: FSMContext
# ):
#     email = message.text if message.text else "-"
#     telegram_id = message.from_user.id
#     fullname = message.from_user.full_name 
#     user_name = message.from_user.username

#     await state.update_data(
#         telegram_id=telegram_id,
#         fullname=fullname,
#         user_name=user_name,
#         email=email
#     )

#     msg_text = f"Это ваш email?:\n\n *{email}*"
#     msg = await message.answer(
#         text=StringConverter.escape_markdown_v2(msg_text),
#         reply_markup=get_yes_no_keyboard(
#             callback_prefix="email",
#             statement="мой email"
#         ),
#         parse_mode="MarkdownV2"
#     )
#     await state.update_data(
#         message_id_to_delete=msg.message_id
#     )
#     await state.set_state(SellerStates.waiting_for_tap_to_keyboard_email)



# @router.callback_query(F.data.startswith("email_") , StateFilter(SellerStates.waiting_for_tap_to_keyboard_email))
# async def callback_org_name(
#     callback: CallbackQuery,
#     state: FSMContext,
#     db_session_factory: async_sessionmaker
# ):
#     await callback.answer()
#     seller_data = await state.get_data() 
#     message_id_to_delete = seller_data["message_id_to_delete"]
#     telegram_id = seller_data["telegram_id"]
#     fullname = seller_data["fullname"]
#     user_name = seller_data["user_name"]
#     email = seller_data["email"]
    
#     await callback.bot.delete_message(
#         chat_id=callback.message.chat.id,
#         message_id=message_id_to_delete
#     )
#     del seller_data['message_id_to_delete']
#     await state.set_data(seller_data)
    
#     if callback.data == "email_yes":  
#         async with db_session_factory() as session:
#             # Проверяем, есть ли пользователь в бд 
#             result = await session.execute(
#                 select(UserORM).where(UserORM.telegram_id == telegram_id)
#             )
#             user_exist = result.scalar_one_or_none()
#             if not user_exist:
#                 user = UserORM(
#                     telegram_id=telegram_id,
#                     fullname=fullname,
#                     user_name=user_name,
#                     email=email
#                 )
#                 session.add(user)
#                 await session.commit()
#                 logging.info(f"added {telegram_id} into 'users' table")
                
#                 # session.refresh(user) — подтянет user.id
#                 await session.refresh(user)   
            
#                 # Сохраняем user_id в FSM
#                 await state.update_data(user_id=user.id)
#                 text = "Спасибо! email и ваши данные telegram записаны😊"
#                 await callback.message.answer(
#                     text=StringConverter.escape_markdown_v2(text),
#                     parse_mode="MarkdownV2"
#                 )
#         text = "Теперь давайте зарегистрируем ваши кабинеты, выберите пункт *Добавить кабинет* в меню"
#         await callback.message.answer(
#             text=StringConverter.escape_markdown_v2(text),
#             reply_markup=kb_add_cabinet,
#             parse_mode="MarkdownV2"
#         )
        
#         await state.set_state(SellerStates.waiting_for_tap_to_menu)
#     else:
#         text = "Хорошо, тогда отправьте свой email ещё раз"
#         await callback.message.answer(
#             text=StringConverter.escape_markdown_v2(text),
#             parse_mode="MarkdownV2"
#         )
#         await state.set_state(SellerStates.email)


# @router.message(StateFilter(SellerStates.waiting_for_tap_to_keyboard_email))
# async def waiting_for_tap_to_keyboard_gs(message: Message):
#     text = "Пожалуйста, нажмите на кнопку выше."
#     await message.answer(
#         text=StringConverter.escape_markdown_v2(text),
#         parse_mode="MarkdownV2"
#     )