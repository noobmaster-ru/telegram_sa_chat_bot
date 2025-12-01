import asyncio
import logging
from aiogram import Bot, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from aiogram.methods import ReadBusinessMessage

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from src.db.models import CabinetORM
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.client import ClientStates
from src.apis.google_sheets_class import GoogleSheetClass
from src.bot.utils.last_activity import update_last_activity
from src.core.config import constants

from .router import router


@router.business_message(F.text.startswith("/link_"))
async def link_cabinet(
    message: Message,
    db_session_factory: async_sessionmaker,
):
    business_connection_id = getattr(message, "business_connection_id", None)
    if not business_connection_id:
        await message.answer("Не удалось определить business_connection_id.")
        return

    code = message.text.removeprefix("/link_").strip()
    if not code:
        await message.answer("Код привязки не найден.")
        return

    async with db_session_factory() as session:
        stmt = select(CabinetORM).where(CabinetORM.link_code == code)
        result = await session.execute(stmt)
        cabinet = result.scalar_one_or_none()

        if cabinet is None:
            await message.answer(
                f"Кабинет с таким кодом не найден. Проверьте код в {constants.SELLERS_BOT_USERNAME}"
            )
            return

        cabinet.business_connection_id = business_connection_id
        cabinet.link_code = None
        await session.commit()

    await message.answer("Кабинет успешно привязан к бизнес-аккаунту ✅")


@router.business_message(StateFilter(constants.SKIP_MESSAGE_STATE))
async def skip_message(message: Message, bot: Bot):
    logging.info(f"user {message.from_user.id} text while we're processing him")


# business_message - only for business account, handler for first message from clients
@router.business_message(StateFilter(None))
async def handle_first_message(
    message: Message,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    cabinet: CabinetORM,
    INSTRUCTION_SHEET_NAME: str,
    bot: Bot,
):
    # 0. Проверяем, что у нас есть кабинет и таблица
    if cabinet is None or spreadsheet is None:
        await message.answer(
            "Техническая ошибка: кабинет ещё не привязан, попробуйте позже."
        )
        return

    await state.set_state(constants.SKIP_MESSAGE_STATE)

    # 1. Выбираем артикул для этого кабинета
    article_obj = cabinet.articles[0] if cabinet.articles else None
    if article_obj is None:
        await message.answer(
            "Для этого кабинета ещё не настроен артикул для раздачи. "
            "Попросите, пожалуйста, менеджера завершить настройку."
        )
        return

    available_nm_id = article_obj.article  # nm_id из ArticleORM
    organization_name = cabinet.organization_name  # название магазина/ИП
    nm_id_name = cabinet.nm_id_name
    
    telegram_id = message.from_user.id
    username = message.from_user.username or "-"
    full_name = message.from_user.full_name or "-"
    text = message.text or "-"
    business_connection_id = message.business_connection_id
    bot_id = message.bot.id

    logging.info(
        f"FIRST MESSAGE from (@{username}, {full_name}), id={telegram_id}: {text} ..."
    )

    # 2. Сохраняем контекст в FSM
    await state.update_data(
        clients_bot_id=bot_id,
        nm_id=available_nm_id,
        organization_name=organization_name,
        nm_id_name=nm_id_name,
        telegram_id=telegram_id,
        full_name=full_name,
        business_connection_id=business_connection_id,
        last_messages_ids=[],
    )

    # 3. Достаём инструкцию именно для этого товара/кабинета
    instruction_str = await spreadsheet.get_instruction(
        sheet_instruction=INSTRUCTION_SHEET_NAME,
        product_title=nm_id_name,
    )

    # 4. Сохраняем покупателя в ТАБЛИЦУ КОНКРЕТНОГО КАБИНЕТА
    await spreadsheet.add_new_buyer(
        username=username,
        full_name=full_name,
        telegram_id=telegram_id,
        nm_id=available_nm_id,
    )

    # небольшая задержка
    await asyncio.sleep(constants.FIRST_MESSAGE_DELAY_SLEEP)

    # помечаем сообщение как прочитанное
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id,
        )
    )

    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await message.answer(text="Здравствуйте!")

    # блок с «печатает» и текстами
    for _ in range(4):
        await bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING,
            business_connection_id=business_connection_id,
        )
        await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)

    await message.answer(
        text=(
            "Сейчас пришлю вам мою подробную инструкцию, пожалуйста, выполняйте все условия!! "
            "Вам также будет помогать мой робот-помощник🤖, вы не пугайтесь😂 , он поможет "
            "быстрее собрать все нужные данные, реквизиты, затем я их проверю и пришлю вам деньги ☺️."
        )
    )

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await message.answer(text="Вот инструкция")

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await message.answer(
        text=instruction_str,
        parse_mode="MarkdownV2",
    )

    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    msg = await message.answer(
        f"Здравствуйте! Я - 🤖-помощник {constants.MANAGER_NAME}.\n"
        f"Вы согласны на наши условия кэшбека?",
        reply_markup=get_yes_no_keyboard("agree", "согласен(на)"),
    )
    await state.set_state(ClientStates.waiting_for_agreement)
    await update_last_activity(state, msg)