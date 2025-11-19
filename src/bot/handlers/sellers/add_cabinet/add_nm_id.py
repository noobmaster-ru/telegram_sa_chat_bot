# import logging
# from aiogram import  F
# from aiogram.filters import StateFilter
# from aiogram.types import Message
# from aiogram.fsm.context import FSMContext
# from sqlalchemy.ext.asyncio import async_sessionmaker

# from src.db.models import ArticleORM

# from src.bot.states.seller import SellerStates
# from .router import router


# @router.message(F.text, StateFilter(SellerStates.waiting_for_nm_id))
# async def handle_nm_id(message: Message, state: FSMContext):
#     text = message.text.strip()

#     if not text.isdigit():
#         return await message.answer("Введите артикул числом (только цифры).")

#     nm_id = int(text)

#     await state.update_data(nm_id=nm_id)

#     await message.answer("Введите количество раздач для этого артикула:")
#     await state.set_state(SellerStates.waiting_for_nm_id_amount)
    
# @router.message(F.text, StateFilter(SellerStates.waiting_for_nm_id_amount))
# async def handle_nm_id_amount(message: Message, state: FSMContext):
#     text = message.text.strip()

#     if not text.isdigit():
#         return await message.answer("Количество раздач должно быть числом.")

#     amount = int(text)

#     await state.update_data(amount=amount)

#     await message.answer("Теперь отправьте фото товара (как изображение, не как файл).")
#     await state.set_state(SellerStates.waiting_for_nm_id_photo)


# @router.message(F.photo, StateFilter(SellerStates.waiting_for_nm_id_photo))
# async def handle_nm_id_photo(
#     message: Message,
#     state: FSMContext,
#     db_session_factory: async_sessionmaker
# ):
#     data = await state.get_data()

#     nm_id = data["nm_id"]
#     amount = data["amount"]
#     cabinet_id = data["cabinet_id"]  # должен быть установлен ранее в cmd_start

#     file_id = message.photo[-1].file_id
#     async with db_session_factory() as session:
#         # Создаём объект ORM
#         new_article = ArticleORM(
#             cabinet_id=cabinet_id,
#             article=nm_id,
#             giveaways=amount,
#             photo_file_id=file_id,
#         )

#         session.add(new_article)
#         await session.commit()

#     await message.answer("Артикул успешно добавлен! 🎉")
#     # очищаем только состояние юзера!!!
#     await state.set_state(state=SellerStates.waiting_for_tap_to_menu)

# @router.message(StateFilter(SellerStates.waiting_for_nm_id_photo))
# async def not_photo_warning(message: Message):
#     await message.answer("Пожалуйста, отправьте фото товара.")