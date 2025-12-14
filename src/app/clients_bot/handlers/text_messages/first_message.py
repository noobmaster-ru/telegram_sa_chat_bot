import json
import asyncio
import logging
from aiogram import Bot, F
from redis.asyncio import Redis
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from aiogram.methods import ReadBusinessMessage

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.states.client import ClientStates
from src.app.bot.utils.last_activity import update_last_activity
from src.infrastructure.apis.google_sheets_class import GoogleSheetClass
from src.infrastructure.db.models import CabinetORM
from src.tools.string_converter_class import StringConverter

from src.core.config import constants

from .router import router

@router.business_message(F.text.startswith("/link_"))
async def link_cabinet(
    message: Message,
    db_session_factory: async_sessionmaker,
):
    business_connection_id = message.business_connection_id
    bot_id = message.bot.id

    if not business_connection_id:
        text="Не удалось определить business_connection_id."
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    code = message.text.removeprefix("/link_").strip()
    if not code:
        text = "Код привязки не найден."
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    async with db_session_factory() as session:
        stmt = select(CabinetORM).where(CabinetORM.link_code == code)
        result = await session.execute(stmt)
        cabinet = result.scalar_one_or_none()

        if cabinet is None:
            text = f"Кабинет с таким кодом не найден. Проверьте код в {constants.SELLERS_BOT_USERNAME}"
            await message.answer(
                text=StringConverter.escape_markdown_v2(text),
                parse_mode="MarkdownV2"
            )
            return

        cabinet.business_connection_id = business_connection_id
        cabinet.link_code = None
        await session.commit()

    text = f"business_connection_id = `{business_connection_id}`"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )
    text = f"Теперь перешлите моё сообщение боту @username_to_id_bot, он вам выдаст мой ID (id: ...) затем перейдите в {constants.SELLERS_BOT_USERNAME} , нажмите на кнопку `Да, связал(а)` и отправьте полученный ID 🙃"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )



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
    bot: Bot,
    redis: Redis
):
    # 0. Проверяем, что у нас есть кабинет и таблица
    if cabinet is None or spreadsheet is None:
        text = "Техническая ошибка: кабинет ещё не привязан, попробуйте позже. (wait link_... message)"
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    await state.set_state(constants.SKIP_MESSAGE_STATE)
    business_connection_id = message.business_connection_id
    redis_key = f"CABINET_SETTINGS:{business_connection_id}:product_settings"
    raw = await redis.get(redis_key)
    product_settings = None
    if raw is None:
        # ❶ Либо лениво достаём настройки из таблицы:
        settings = await spreadsheet.get_data_from_settings_sheet()
        # settings = {...} — то, что возвращает твой метод
        # и можно сразу положить в Redis, чтобы в следующий раз было из кэша
        await redis.set(redis_key, json.dumps(settings))
        product_settings = settings
    else:
        # raw = bytes или str, json.loads это понимает
        product_settings = json.loads(raw)
    
    # settings = {
    #     "nm_id": nm_id,
    #     "image_url": image_url,
    #     "nm_id_name": nm_id_name,
    #     "brand_name": brand_name,
    #     "instruction": instruction
    # }
    nm_id = product_settings["nm_id"]
    image_url = product_settings["image_url"]
    nm_id_name = product_settings["nm_id_name"]
    brand_name = product_settings["brand_name"]
    instruction = product_settings["instruction"]
    
    # # 1. Выбираем артикул для этого кабинета
    # article_obj = cabinet.articles[0] if cabinet.articles else None
    # if article_obj is None:
    #     text = (
    #         "Для этого кабинета ещё не настроен артикул для раздачи. "
    #         "Попросите, пожалуйста, менеджера завершить настройку."
    #     )
    #     await message.answer(
    #         text=StringConverter.escape_markdown_v2(text),
    #         parse_mode="MarkdownV2"
    #     )
    #     return

    # available_nm_id = article_obj.article  # nm_id из ArticleORM
    # organization_name = cabinet.organization_name  # название магазина/ИП
    # nm_id_name = cabinet.nm_id_name
    
    telegram_id = message.from_user.id
    username = message.from_user.username or "-"
    full_name = message.from_user.full_name or "-"
    msg_text = message.text or "-"
    bot_id = message.bot.id

    logging.info(
        f"FIRST MESSAGE from (@{username}, {full_name}), id={telegram_id}: {msg_text} ..."
    )

    # 2. Сохраняем контекст в FSM
    await state.update_data(
        clients_bot_id=bot_id,
        nm_id=nm_id,
        brand_name=brand_name,
        nm_id_name=nm_id_name,
        image_url=image_url,
        instruction=instruction,
        telegram_id=telegram_id,
        full_name=full_name,
        business_connection_id=business_connection_id,
        last_messages_ids=[],
    )

    # # 3. Достаём инструкцию именно для этого товара/кабинета
    # instruction_str = await spreadsheet.get_instruction(
    #     sheet_settings=constants.SETTINGS_SHEET_NAME_STR
    # )

    # 4. Сохраняем покупателя в ТАБЛИЦУ КОНКРЕТНОГО КАБИНЕТА
    await spreadsheet.add_new_buyer(
        username=username,
        full_name=full_name,
        telegram_id=telegram_id,
        nm_id=nm_id,
        msg_text=msg_text
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
    text = "Здравствуйте!"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )

    # блок с «печатает» и текстами
    for _ in range(4):
        await bot.send_chat_action(
            chat_id=message.chat.id,
            action=ChatAction.TYPING,
            business_connection_id=business_connection_id,
        )
        await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)

    text = (
        "Сейчас пришлю вам мою подробную инструкцию, пожалуйста, выполняйте все условия!! "
        "Вам также будет помогать мой робот-помощник🤖, вы не пугайтесь😂 , он поможет "
        "быстрее собрать все нужные данные, реквизиты, затем я их проверю и пришлю вам деньги ☺️."
    )
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    text = "Вот инструкция"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await message.answer(
        text=StringConverter.escape_markdown_v2(instruction),
        parse_mode="MarkdownV2",
    )

    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    text = (
        f"Здравствуйте! Я - 🤖-помощник.\n"
        f"Вы согласны на наши условия кэшбека?"
    )
    msg = await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=get_yes_no_keyboard("agree", "согласен(на)"),
        parse_mode="MarkdownV2"
    )
    await state.set_state(ClientStates.waiting_for_agreement)
    await update_last_activity(state, msg)