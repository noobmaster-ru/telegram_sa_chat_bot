import logging
from aiogram import F
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
    text = (message.text or "").strip()
    seller_data = await state.get_data()
    organization_name = seller_data.get("organization_name", "-")

    if not text.isdigit():
        return await message.answer(
            "Введите артикул числом, *только цифры*",
            parse_mode="MarkdownV2",
        )

    nm_id = int(text)
    await state.update_data(nm_id=nm_id)

    await message.answer(
        f"Организация: *{organization_name}*\n"
        f"Артикул: *{nm_id}*\n\n"
        f"Введите название товара\\(*ОЧЕНЬ ВАЖНО УКАЗАТЬ ИМЕННО ТАК, КАК ТОВАР НАЗЫВАЕТСЯ НА ВБ \\- AI БУДЕТ СРАВНИВАТЬ НАЗВАНИЕ ТОВАРА НА СКРИНШОТАХ*\\):",
        parse_mode="MarkdownV2",
    )
    await state.set_state(SellerStates.waiting_for_nm_id_name)


@router.message(F.text, StateFilter(SellerStates.waiting_for_nm_id_name))
async def handle_nm_id_amount(message: Message, state: FSMContext):
    nm_id_name = (message.text or "").capitalize()
    seller_data = await state.get_data()
    organization_name = seller_data.get("organization_name", "-")
    nm_id = seller_data.get("nm_id")


    await state.update_data(nm_id_name=nm_id_name)

    await message.answer(
        f"Организация: *{organization_name}*\n"
        f"Артикул: *{nm_id}*\n"
        f"Название товара: *{nm_id_name}*\n\n"
        f"Теперь отправьте фото товара, как изображение, не как файл\\.",
        parse_mode="MarkdownV2",
    )
    await state.set_state(SellerStates.waiting_for_nm_id_photo)


@router.message(F.photo, StateFilter(SellerStates.waiting_for_nm_id_photo))
async def handle_nm_id_photo(
    message: Message,
    state: FSMContext,
):
    seller_data = await state.get_data()

    # === 1. Проверяем, не отправил ли пользователь альбом (несколько фоток) ===
    if message.media_group_id is not None:
        last_media_group = seller_data.get("last_media_group_id")

        # если этот альбом уже обрабатывали — выходим
        if last_media_group == message.media_group_id:
            return

        # иначе сохраняем ID альбома и показываем сообщение
        await state.update_data(last_media_group_id=message.media_group_id)
        await message.answer(
            "Пожалуйста, отправьте только одну фотографию: первую фотографию артикула\\.",
            parse_mode="MarkdownV2"
        )
        return

    nm_id = seller_data["nm_id"]
    nm_id_name = seller_data["nm_id_name"]
    organization_name = seller_data.get("organization_name", "-")

    # берём фото в лучшем качестве
    photo_file_id = message.photo[-1].file_id

    await state.update_data(nm_id_photo_file_id=photo_file_id)

    msg = await message.answer_photo(
        photo=photo_file_id,
        caption=(
            f"Организация: *{organization_name}*\n"
            f"Артикул: *{nm_id}*\n"
            f"Название товара: *{nm_id_name}*\n\n\n"
            f"Данные заполнены верно?"
        ),
        reply_markup=get_yes_no_keyboard(
            callback_prefix="data_verify",
            statement="верно",
        ),
        parse_mode="MarkdownV2",
    )
    await state.update_data(
        message_id_to_delete=msg.message_id,
    )


@router.callback_query(F.data.startswith("data_verify"))
async def write_data_into_db(
    callback: CallbackQuery,
    state: FSMContext,
    db_session_factory: async_sessionmaker,
):
    await callback.answer()
    seller_data = await state.get_data()
    message_id_to_delete = seller_data["message_id_to_delete"]

    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=message_id_to_delete,
    )
    del seller_data["message_id_to_delete"]
    await state.set_data(seller_data)

    if callback.data == "data_verify_yes":
        nm_id = seller_data["nm_id"]
        nm_id_name = seller_data["nm_id_name"]
        cabinet_id = seller_data["cabinet_id"]  # установлен в q3_service_account_access
        file_id = seller_data["nm_id_photo_file_id"]
        organization_name = seller_data.get("organization_name", "-")

        async with db_session_factory() as session:
            new_article = ArticleORM(
                cabinet_id=cabinet_id,
                article=nm_id,
                nm_id_name=nm_id_name,
                photo_file_id=file_id,
            )
            session.add(new_article)
            await session.commit()

        await callback.message.answer(
            f"Организация: *{organization_name}*\n"
            f"Артикул: *{nm_id}*\n"
            f"Название товара: *{nm_id_name}*\n\n\n"
            f"Успешно добавлен🎉",
            reply_markup=kb_menu,
            parse_mode="MarkdownV2",
        )
        await state.set_state(SellerStates.waiting_for_tap_to_menu)
    else:
        await callback.message.answer(
            "Хорошо, давайте добавим артикул заново. Отправьте артикул товара на ВБ (число)."
        )
        await state.set_state(SellerStates.waiting_for_nm_id)


@router.message(StateFilter(SellerStates.waiting_for_nm_id_photo))
async def not_photo_warning(message: Message):
    await message.answer("Пожалуйста, отправьте фото товара.")