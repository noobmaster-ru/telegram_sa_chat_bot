import asyncio
import logging
from datetime import UTC, datetime

from aiogram import Bot, Router
from aiogram.enums import ChatAction, ParseMode
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram import inject
from redis.asyncio import Redis

from axiomai.application.interactors.create_buyer import CreateBuyer
from axiomai.config import Config
from axiomai.infrastructure.chat_history import (
    add_predialog_chat_history,
    clear_predialog_chat_history,
    get_predialog_chat_history,
)
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.message_debouncer import MessageData, MessageDebouncer, merge_messages_text
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import determine_resume_state
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates
from axiomai.tgbot.filters.ignore_self_message import SelfBusinessMessageFilter

logger = logging.getLogger(__name__)

router = Router()
router.business_message.filter(~SelfBusinessMessageFilter())


@router.business_message(StateFilter(None))
@inject
async def process_clients_business_message(
    message: Message,
    bot: Bot,
    state: FSMContext,
    dialog_manager: DialogManager,
    di_container: FromDishka[AsyncContainer],
    debouncer: FromDishka[MessageDebouncer],
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
) -> None:
    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(message.business_connection_id)

    if not cabinet:
        logger.warning("no cabinet found for business connection %s, skipping message from chat %s", message.business_connection_id, message.chat.id)
        return

    if cabinet.leads_balance <= 0:
        logger.info("skip message from chat %s due to zero leads balance for cabinet %s", message.chat.id, cabinet.id)
        return

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    # Проверяем, есть ли у пользователя незавершённые заявки — если да, возобновляем диалог
    active_buyers = await buyer_gateway.get_incompleted_buyers_by_telegram_id_and_cabinet_id(
        message.from_user.id, cabinet.id
    )
    resume_state = determine_resume_state(active_buyers) if active_buyers else None
    if resume_state:
        logger.info(
            "resuming dialog for chat %s at state %s with %s active buyers",
            message.chat.id, resume_state, len(active_buyers),
        )

        await state.set_state("client_processing")
        await dialog_manager.start(
            resume_state,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.SEND,
        )
        return

    message_text = message.text or message.caption or ""

    photo_url = None
    if message.photo:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    message_data = MessageData(
        text=message_text,
        timestamp=datetime.now(UTC).timestamp(),
        message_id=message.message_id,
        has_photo=bool(message.photo),
        photo_url=photo_url,
    )
    bg_manager = dialog_manager.bg()
    app_container = di_container.parent_container

    await debouncer.add_message(
        business_connection_id=message.business_connection_id,
        chat_id=message.chat.id,
        message_data=message_data,
        process_callback=lambda biz_id, chat_id, msgs: _process_accumulated_messages(
            biz_id, chat_id, message.from_user.username, message.from_user.full_name, msgs, bot, state, bg_manager, app_container
        ),
    )


async def _process_accumulated_messages(
    business_connection_id: str,
    chat_id: int,
    username: str | None,
    fullname: str,
    messages: list[MessageData],
    bot: Bot,
    state: FSMContext,
    dialog_manager: DialogManager,
    di_container: AsyncContainer,
) -> None:
    """Обработка накопленных сообщений после паузы. Вызывается MessageDebouncer автоматически."""
    logger.info("processing %s accumulated messages for chat %s", len(messages), chat_id)

    async with di_container() as r_container:
        config = await r_container.get(Config)
        cashback_table_gateway = await r_container.get(CashbackTableGateway)
        openai_gateway = await r_container.get(OpenAIGateway)
        redis = await r_container.get(Redis)

        cashback_table = await cashback_table_gateway.get_active_cashback_table_by_business_connection_id(
            business_connection_id
        )

        if not cashback_table:
            await bot.send_message(
                chat_id=chat_id,
                text="Таблица кешбека не найдена или не активна.",
                business_connection_id=business_connection_id,
            )
            return

        articles = await cashback_table_gateway.get_in_stock_cashback_articles_by_cabinet_id(
            cabinet_id=cashback_table.cabinet_id, telegram_id=chat_id
        )

        if not articles:
            await bot.send_message(
                chat_id=chat_id,
                text="Увы, артикулы для раздачи кэшбека закончились.",
                business_connection_id=business_connection_id,
            )
            return

    chat_history = await get_predialog_chat_history(redis, business_connection_id, chat_id)

    combined_text = merge_messages_text(messages)

    photo_urls = [msg.photo_url for msg in messages if msg.photo_url]
    photo_url = photo_urls[0] if photo_urls else None

    logger.debug("combined text: %s...", combined_text[:100])
    logger.debug("photo urls: %s", len(photo_urls))

    result = await openai_gateway.chat_with_client(
        user_message=combined_text,
        articles=articles,
        chat_history=chat_history,
        photo_url=photo_url,
    )

    response_text = result["response"]
    classified_article_id = result["article_id"]

    await bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(config.delay_between_bot_messages)

    if classified_article_id:
        await add_predialog_chat_history(redis, business_connection_id, chat_id, combined_text, response_text)

        await bot.send_message(
            chat_id=chat_id,
            text=response_text,
            business_connection_id=business_connection_id,
            parse_mode=ParseMode.MARKDOWN,
        )

        predialog_history = await get_predialog_chat_history(redis, business_connection_id, chat_id)
        await clear_predialog_chat_history(redis, business_connection_id, chat_id)

        await state.set_state("client_processing")

        async with di_container() as r_container:
            create_buyer = await r_container.get(CreateBuyer)
            await create_buyer.execute(chat_id, username, fullname, classified_article_id, predialog_history)

        await dialog_manager.start(
            CashbackArticleStates.check_order,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.SEND
        )
    else:
        await add_predialog_chat_history(redis, business_connection_id, chat_id, combined_text, response_text)

        await bot.send_message(
            chat_id=chat_id,
            text=response_text,
            business_connection_id=business_connection_id,
            parse_mode=ParseMode.MARKDOWN,
        )
