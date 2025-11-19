# import logging
# from aiogram import Router, F
# from aiogram.filters import CommandStart, StateFilter
# from aiogram.types import Message
# from aiogram.fsm.context import FSMContext

# from sqlalchemy.ext.asyncio import async_sessionmaker
# from sqlalchemy import select
# from src.bot.keyboards.reply.menu import kb_menu
# from src.db.models import UserORM
# from src.bot.states.seller import SellerStates
# from .router import router


# @router.message(CommandStart())
# async def cmd_start(
#     message: Message,
#     state: FSMContext,
#     db_session_factory: async_sessionmaker
# ):
#     telegram_id = message.from_user.id
#     fullname = message.from_user.full_name 
    
#     await state.update_data(
#         telegram_id=telegram_id
#     )
#     await message.answer(f"Здравствуйте!")
#     await message.answer(
#         "Давайте зарегистрируем ваши кабинеты, выберите пункт 'Добавить кабинет' в меню",
#         reply_markup=kb_menu
#     )
#     async with db_session_factory() as session:
#         # Проверяем, есть ли пользователь в бд 
#         result = await session.execute(
#             select(UserORM).where(UserORM.telegram_id == telegram_id)
#         )
#         user_exist = result.scalar_one_or_none()
#         if not user_exist:
#             user = UserORM(
#                 telegram_id=telegram_id,
#                 fullname=fullname
#             )
#             session.add(user)
#             await session.commit()
#             logging.info(f"added {telegram_id} into 'users' table")
            
#             # session.refresh(user) — подтянет user.id
#             await session.refresh(user)   
        
#             # Сохраняем user_id в FSM
#             await state.update_data(user_id=user.id)
#     await state.set_state(SellerStates.waiting_for_tap_to_menu)
    
    