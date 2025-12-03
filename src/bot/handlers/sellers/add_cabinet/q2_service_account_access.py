import logging
from pathlib import Path
from aiogram import F, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.types import FSInputFile, InputMediaPhoto, Message, CallbackQuery

from src.db.models import (
    CabinetORM,
    CashbackTableORM,
    CashbackTableStatus,
)
from src.bot.states.seller import SellerStates
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.tools.string_converter_class import StringConverter
from src.core.config import constants, settings

from .router import router
import secrets
import string


def generate_link_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.callback_query(
    F.data.startswith("service_account"),
    StateFilter(SellerStates.add_cabinet_to_db),
)
async def handle_add_service_account_into_gs(
    callback: CallbackQuery,
    state: FSMContext,
    db_session_factory: async_sessionmaker,
    bot: Bot,
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

    if callback.data == "service_account_yes":
        google_sheets_url = seller_data["google_sheets_url"]
        user_id = seller_data["user_id"]
        organization_name = seller_data["organization_name"]
        nm_id_name = "" #seller_data["nm_id_name"]
        # Разбираем ссылку и достаём table_id (spreadsheet_id)
        part1 = google_sheets_url.split("/d/")[-1]
        table_id = part1.split("/edit")[0]

        link_code = generate_link_code()

        async with db_session_factory() as session:
            # 1. создаём кабинет
            new_cabinet = CabinetORM(
                user_id=user_id,
                organization_name=organization_name,
                link_code=link_code,
                nm_id_name=nm_id_name,
                leads_balance=0
            )
            session.add(new_cabinet)
            await session.flush()  # получим new_cabinet.id без коммита

            # 2. создаём таблицу кэшбека для этого кабинета
            cashback_table = CashbackTableORM(
                cabinet_id=new_cabinet.id,
                table_id=table_id,
                status=CashbackTableStatus.NEW,
            )
            session.add(cashback_table)

            await session.commit()
            await session.refresh(new_cabinet)
            await session.refresh(cashback_table)

            # сохраняем в FSM id кабинета и таблицы (пригодится дальше)
            await state.update_data(
                cabinet_id=new_cabinet.id,
                cashback_table_id=cashback_table.id,
            )
        text = f"✅ Магазин: *{organization_name}* успешно добавлен!"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        text = (
            f"1.Подключите {constants.CLIENTS_BOT_USERNAME} как чат-бот к вашему бизнес-аккаунту.\n"
            "2. Отправьте *от своего личного аккаунта* вот такое сообщение бизнес-аккаунту:\n\n"
            f"/link_{link_code}"
            "\n\nЭто нужно сделать один раз, чтобы *связать бота с бизнес-аккаунтом*."
            "Если всё хорошо, то ваш бизнес-аккаунт должен отправить вам сообщение:\n\n"
            "*Кабинет успешно привязан к бизнес-аккаунту ✅*\n\n"
            "Дальше вам свой же бизнес-аккаунт скажет что делать🫨"
        )
        msg = await callback.message.answer(
            text = StringConverter.escape_markdown_v2(text),
            reply_markup=get_yes_no_keyboard(
                callback_prefix="link_bot",  # префикс оставляем, чтобы не ломать остальную логику
                statement="связал(а)",
            ),
            parse_mode="MarkdownV2"
        )
        await state.update_data(
            message_id_to_delete=msg.message_id
        )
        await state.set_state(SellerStates.waiting_for_link_bot_to_bus_acc)

    else:
        await callback.message.answer(
            "Пожалуйста, добавьте сервисный аккаунт в Google-таблицу, "
            "без добавления мы не сможем записывать данные в вашу таблицу."
        )
        await callback.message.answer("Вот подробная инструкция")
        INSTRUCTION_PHOTOS_DIR = constants.INSTRUCTION_PHOTOS_DIR
        photo_path1 = INSTRUCTION_PHOTOS_DIR + "1_access_settings.png"
        photo_path2 = INSTRUCTION_PHOTOS_DIR + "2_search_bar.png"
        photo_path3 = INSTRUCTION_PHOTOS_DIR + "3_access_axiomai_editor.png"
        photo_path4 = INSTRUCTION_PHOTOS_DIR + "4_axiomai_service_account.png"

        caption_text = (
            f"Теперь *внимательно!*:\n\n"
            f"1. Откройте свою таблицу\n"
            f"2. В правом верхнем углу откройте настройки доступа *(фото1)*\n"
            f"3. В поисковой строке вбейте вот этот email *(фото2)*:\n\n"
            f"*{settings.SERVICE_ACCOUNT_AXIOMAI_EMAIL}*\n\n"
            f"4. Дайте доступ *Редактор* этому сервисному аккаунту Google *(фото3)*\n\n"
            f"Как сделаете, у вас должно получиться вот так, как на *(фото4)*"
        )
        safe_caption = StringConverter.escape_markdown_v2(caption_text)
        media_group = [
            InputMediaPhoto(
                media=FSInputFile(photo_path1),
                caption=safe_caption,
                parse_mode="MarkdownV2",
            ),
            InputMediaPhoto(media=FSInputFile(photo_path2)),
            InputMediaPhoto(media=FSInputFile(photo_path3)),
            InputMediaPhoto(media=FSInputFile(photo_path4)),
        ]
        await bot.send_media_group(
            chat_id=callback.message.chat.id,
            media=media_group,
        )
        msg = await callback.message.answer(
            "Дали доступ *Редактор* нашему cервисному аккаунту Google?",
            reply_markup=get_yes_no_keyboard(
                callback_prefix="service_account",
                statement="дал",
            ),
            parse_mode="MarkdownV2",
        )
        await state.update_data(
            message_id_to_delete=msg.message_id,
        )


@router.message(StateFilter(SellerStates.add_cabinet_to_db))
async def waiting_for_tap_to_keyboard_add_cabine_to_db(message: Message):
    await message.answer("Пожалуйста, нажмите на кнопку выше.")