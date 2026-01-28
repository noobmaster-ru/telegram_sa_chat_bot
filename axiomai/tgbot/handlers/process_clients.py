import asyncio
import logging
from datetime import UTC, datetime

from aiogram import Bot, Router
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram import inject

from axiomai.constants import DELAY_BEETWEEN_BOT_MESSAGES
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.message_debouncer import MessageData, MessageDebouncer, merge_messages_text
from axiomai.infrastructure.openai import OpenAIGateway
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
    di_container: AsyncContainer,
    debouncer: FromDishka[MessageDebouncer],
) -> None:
    """
    Обработчик входящих сообщений от клиентов.
    Накапливает сообщения через MessageDebouncer и обрабатывает после паузы.
    """
    if not message.business_connection_id:
        logger.warning("received message without business_connection_id")
        return

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

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
    await debouncer.add_message(
        business_connection_id=message.business_connection_id,
        chat_id=message.chat.id,
        message_data=message_data,
        process_callback=lambda biz_id, chat_id, msgs: _process_accumulated_messages(
            biz_id, chat_id, msgs, bot, state, bg_manager, di_container
        ),
    )


async def _process_accumulated_messages(
    business_connection_id: str,
    chat_id: int,
    messages: list[MessageData],
    bot: Bot,
    state: FSMContext,
    dialog_manager: DialogManager,
    di_container: AsyncContainer,
) -> None:
    """
    Обработка накопленных сообщений после паузы.
    Вызывается MessageDebouncer автоматически.
    """
    logger.info("processing %s accumulated messages for chat %s", len(messages), chat_id)

    async with di_container() as r_container:
        cashback_table_gateway = await r_container.get(CashbackTableGateway)
        openai_gateway = await r_container.get(OpenAIGateway)

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

        articles = await cashback_table_gateway.get_in_stock_cashback_articles_by_cabinet_id(cashback_table.cabinet_id)

        if not articles:
            await bot.send_message(
                chat_id=chat_id,
                text="Увы, артикулы для раздачи кэшбека закончились",
                business_connection_id=business_connection_id,
            )
            return

        combined_text = merge_messages_text(messages)

        photo_urls = [msg.photo_url for msg in messages if msg.photo_url]
        photo_url = photo_urls[0] if photo_urls else None

        logger.debug("combined text: %s...", combined_text[:100])
        logger.debug("photo urls: %s", len(photo_urls))

        classified_article = await openai_gateway.classify_article_from_message(combined_text, articles, photo_url)

        await bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING,
            business_connection_id=business_connection_id,
        )
        await asyncio.sleep(DELAY_BEETWEEN_BOT_MESSAGES)
        if classified_article:
            await state.set_state("client_processing")
            await dialog_manager.start(
                CashbackArticleStates.check_order,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.SEND,
                data={
                    "article_id": classified_article.id,
                    "telegram_id": chat_id,
                    "username": None,  # Will be set from message.from_user in dialog
                    "fullname": "",  # Will be set from message.from_user in dialog
                },
            )
        else:
            articles_text = "\n".join(f"- {article.title}" for article in articles)
            response_text = f"Текущие артикулы для раздачи кешбека:\n{articles_text}"

            await bot.send_message(
                chat_id=chat_id,
                text=response_text,
                business_connection_id=business_connection_id,
            )


@router.business_message(StateFilter("skip_messaging"))
async def skip_messaging(message: Message, bot: Bot) -> None:
    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)
