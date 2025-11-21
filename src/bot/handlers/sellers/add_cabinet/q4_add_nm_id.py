import logging
from aiogram import  F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.db.models import ArticleORM
from src.bot.keyboards.reply.menu import kb_menu
from src.bot.states.seller import SellerStates
from .router import router


@router.message(F.text, StateFilter(SellerStates.waiting_for_nm_id))
async def handle_nm_id(message: Message, state: FSMContext):
    text = message.text.strip()

    if not text.isdigit():
        return await message.answer(
            "Введите артикул числом, *только цифры*",
            parse_mode="MarkdownV2"
        )

    nm_id = int(text)

    await state.update_data(nm_id=nm_id)

    await message.answer(
        f"Артикул: *{nm_id}*\n\nВведите количество раздач для этого артикула:",
        parse_mode="MarkdownV2"
    )
    await state.set_state(SellerStates.waiting_for_nm_id_amount)
    
@router.message(F.text, StateFilter(SellerStates.waiting_for_nm_id_amount))
async def handle_nm_id_amount(message: Message, state: FSMContext):
    text = message.text.strip()

    if not text.isdigit():
        return await message.answer("Количество раздач должно быть целым *числом.*")

    amount = int(text)
    
    await state.update_data(amount=amount)
    seller_data = await state.get_data()
    await message.answer(
        f"Артикул: *{seller_data["nm_id"]}*\nКоличество раздач: *{amount}*\n\n"
        "Теперь отправьте фото товара ,как изображение, не как файл",
        parse_mode="MarkdownV2"
    )
    await state.set_state(SellerStates.waiting_for_nm_id_photo)


@router.message(F.photo, StateFilter(SellerStates.waiting_for_nm_id_photo))
async def handle_nm_id_photo(
    message: Message,
    state: FSMContext
):
    seller_data = await state.get_data()
    # === 1. Проверяем, не отправил ли пользователь альбом(несколько фоток) ===
    if message.media_group_id is not None:
        last_media_group = seller_data.get("last_media_group_id")
        
        # если этот альбом уже обрабатывали — выходим
        if last_media_group == message.media_group_id:
            return
        
        # иначе сохраняем ID альбома и показываем сообщение
        await state.update_data(last_media_group_id=message.media_group_id)
        await message.answer("Пожалуйста, отправьте только одну фотографию: первую фотографию артикула.")
        return


    nm_id = seller_data["nm_id"]
    amount = seller_data["amount"]


    photo_file_id = message.photo[-1].file_id # в лучшем качестве
    
    await state.update_data(nm_id_photo_file_id=photo_file_id)
    # Отправляем фотографию обратно, используя этот file_id
    msg = await message.answer_photo(
        photo=photo_file_id,
        caption=f"Получен артикул: *{nm_id}*\nКоличество для раздач: *{amount}*\n\n\n Данные заполнены верно?",
        reply_markup=get_yes_no_keyboard(
            callback_prefix="data_verify",
            statement="верно"
        ),
        parse_mode="MarkdownV2"
    )
    await state.update_data(
        message_id_to_delete=msg.message_id
    )
    
@router.callback_query(F.data.startswith("data_verify"))
async def write_data_into_db(
    callback: CallbackQuery,
    state: FSMContext,
    db_session_factory: async_sessionmaker
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
    if callback.data == "data_verify_yes":
        nm_id = seller_data["nm_id"]
        amount = seller_data["amount"]
        cabinet_id = seller_data["cabinet_id"]  # должен быть установлен ранее в cmd_start
        file_id = seller_data["nm_id_photo_file_id"]
        
        async with db_session_factory() as session:
            # Создаём объект ORM
            new_article = ArticleORM(
                cabinet_id=cabinet_id,
                article=nm_id,
                giveaways=amount,
                photo_file_id=file_id,
            )

            session.add(new_article)
            await session.commit()

        await callback.message.answer(
            "Артикул успешно добавлен! 🎉",
            reply_markup=kb_menu
        )
        # очищаем только состояние юзера!!!
        await state.set_state(state=SellerStates.waiting_for_tap_to_menu)
    else:
        await callback.message.answer("Хорошо, давайте добавим артикул заново. Отправьте артикул товара на ВБ (число)")
        await state.set_state(SellerStates.waiting_for_nm_id)
      
@router.message(StateFilter(SellerStates.waiting_for_nm_id_photo))
async def not_photo_warning(message: Message):
    await message.answer("Пожалуйста, отправьте фото товара.")