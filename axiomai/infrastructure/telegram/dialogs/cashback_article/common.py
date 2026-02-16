import asyncio
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.interactors.create_buyer import CreateBuyer
from axiomai.config import Config
from axiomai.infrastructure.chat_history import add_to_chat_history, get_chat_history
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.models import Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackArticle
from axiomai.infrastructure.message_debouncer import MessageData, MessageDebouncer, merge_messages_text
from axiomai.infrastructure.openai import ArticleInfo, OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates


def get_pending_nm_ids_for_step(buyers: list[Buyer], step: str) -> list[int]:
    if step == "check_order":
        return [b.nm_id for b in buyers if not b.is_ordered]
    if step == "check_received":
        return [b.nm_id for b in buyers if b.is_ordered and not b.is_left_feedback]
    if step == "check_labels_cut":
        return [b.nm_id for b in buyers if b.is_left_feedback and not b.is_cut_labels]

    return []


def build_articles_for_gpt(articles: list[CashbackArticle]) -> list[ArticleInfo]:
    return [
        ArticleInfo(
            id=a.id,
            nm_id=a.nm_id,
            title=a.title,
            brand_name=a.brand_name,
            image_url=a.image_url,
            instruction_text=a.instruction_text,
        )
        for a in articles
    ]


@inject
async def mes_input_handler(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    debouncer: FromDishka[MessageDebouncer],
    di_container: FromDishka[AsyncContainer],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]
    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if message.text == "stop":
        await dialog_manager.done()
        return

    if message.text:
        message_data = MessageData(
            text=message.text,
            timestamp=datetime.now(UTC).timestamp(),
            message_id=message.message_id,
            has_photo=False,
            photo_url=None,
            chat_id=message.chat.id,
        )

        bg_manager = dialog_manager.bg()
        app_container = di_container.parent_container
        current_state = dialog_manager.current_context().state
        step_name = current_state.state.split(":")[-1] if current_state else "unknown"

        await debouncer.add_message(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_data=message_data,
            process_callback=lambda biz_id, chat_id, msgs: _process_dialog_messages(
                biz_id, chat_id, message.from_user.username, message.from_user.full_name, msgs, bot, app_container, step_name, bg_manager
            ),
        )
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await dialog_manager.show(ShowMode.SEND)


async def _process_dialog_messages(
    business_connection_id: str,
    chat_id: int,
    username: str | None,
    fullname: str,
    messages: list[MessageData],
    bot: Bot,
    di_container: AsyncContainer,
    step_name: str,
    bg_manager: DialogManager,
) -> None:
    async with di_container() as r_container:
        config = await r_container.get(Config)
        openai_gateway = await r_container.get(OpenAIGateway)
        cashback_table_gateway = await r_container.get(CashbackTableGateway)
        cabinet_gateway = await r_container.get(CabinetGateway)

        cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(business_connection_id)
        articles = await cashback_table_gateway.get_in_stock_cashback_articles_by_cabinet_id(cabinet.id, chat_id)

    articles_for_gpt = build_articles_for_gpt(articles)
    valid_ids = {art.id for art in articles}

    chat_history = await get_chat_history(di_container, chat_id, cabinet.id)
    combined_text = merge_messages_text(messages)

    result = await openai_gateway.answer_user_question(
        user_message=combined_text,
        current_step=step_name,
        articles=articles_for_gpt,
        chat_history=chat_history,
    )

    response_text = result["response"]
    wants_to_stop = result["wants_to_stop"]
    switch_to_article_id = result["switch_to_article_id"]

    await add_to_chat_history(di_container, chat_id, cabinet.id, combined_text, response_text)

    await bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(config.delay_between_bot_messages)

    await bot.send_message(
        chat_id=chat_id,
        text=response_text,
        business_connection_id=business_connection_id,
        parse_mode=ParseMode.MARKDOWN,
    )

    if switch_to_article_id and switch_to_article_id in valid_ids:
        async with di_container() as r_container:
            create_buyer = await r_container.get(CreateBuyer)
            buyer_gateway = await r_container.get(BuyerGateway)
            await create_buyer.execute(chat_id, username, fullname, switch_to_article_id, [])

            active_buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(
                chat_id, cabinet.id
            )

        await bg_manager.start(
            determine_resume_state(active_buyers),
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.SEND,
        )
        return

    if wants_to_stop:
        await bg_manager.done()


def determine_resume_state(buyers: list[Buyer]) -> CashbackArticleStates | None:
    """Определяет состояние диалога для возобновления на основе прогресса заявок."""
    has_pending_order = any(not b.is_ordered for b in buyers)
    has_pending_feedback = any(b.is_ordered and not b.is_left_feedback for b in buyers)
    has_pending_labels = any(b.is_left_feedback and not b.is_cut_labels for b in buyers)
    has_pending_requisites = any(
        b.is_cut_labels and not b.is_superbanking_paid and not b.is_paid_manually for b in buyers
    )

    if has_pending_order:
        return CashbackArticleStates.check_order
    if has_pending_feedback:
        return CashbackArticleStates.check_received
    if has_pending_labels:
        return CashbackArticleStates.check_labels_cut
    if has_pending_requisites:
        return CashbackArticleStates.input_requisites

    return None
