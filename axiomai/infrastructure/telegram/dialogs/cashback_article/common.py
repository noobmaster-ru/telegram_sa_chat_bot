import asyncio
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot
from aiogram.enums import ChatAction, ParseMode
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode, StartMode
from aiogram_dialog.widgets.input import MessageInput
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.interactors.create_buyer import CreateBuyer
from axiomai.constants import DELAY_BEETWEEN_BOT_MESSAGES
from axiomai.infrastructure.chat_history import add_to_chat_history, get_chat_history
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.message_debouncer import MessageData, MessageDebouncer, merge_messages_text
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates


async def _get_or_create_buyer(dialog_manager: DialogManager, di_container: AsyncContainer) -> int:
    buyer_id = dialog_manager.dialog_data.get("buyer_id")
    if buyer_id:
        return buyer_id

    async with di_container() as r_container:
        create_buyer = await r_container.get(CreateBuyer)
        event = dialog_manager.event
        user = event.from_user if hasattr(event, "from_user") else None

        buyer = await create_buyer.execute(
            telegram_id=dialog_manager.event.chat.id,
            username=user.username if user else None,
            fullname=user.full_name if user else "",
            article_id=dialog_manager.start_data["article_id"],
        )
        dialog_manager.dialog_data["buyer_id"] = buyer.id
        return buyer.id


async def _update_buyer_field(di_container: AsyncContainer, buyer_id: int, **fields: Any) -> None:
    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        transaction_manager = await r_container.get(TransactionManager)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        if buyer:
            for key, value in fields.items():
                setattr(buyer, key, value)
            await buyer_gateway.update_buyer(buyer)
            await transaction_manager.commit()


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

        current_state = dialog_manager.current_context().state
        step_name = current_state.state.split(":")[-1] if current_state else "unknown"
        article_id = dialog_manager.start_data["article_id"]
        buyer_id = dialog_manager.dialog_data.get("buyer_id")
        bg_manager = dialog_manager.bg()

        await debouncer.add_message(
            business_connection_id=message.business_connection_id,
            chat_id=message.chat.id,
            message_data=message_data,
            process_callback=lambda biz_id, chat_id, msgs: _process_dialog_messages(
                biz_id, chat_id, msgs, bot, di_container, step_name, article_id, buyer_id, bg_manager
            ),
        )
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await dialog_manager.show(ShowMode.SEND)


async def _process_dialog_messages(
    business_connection_id: str,
    chat_id: int,
    messages: list[MessageData],
    bot: Bot,
    di_container: AsyncContainer,
    step_name: str,
    article_id: int,
    buyer_id: int | None,
    bg_manager: DialogManager,
) -> None:
    """Обработка накопленных сообщений внутри диалога"""
    async with di_container() as r_container:
        openai_gateway = await r_container.get(OpenAIGateway)
        cashback_table_gateway = await r_container.get(CashbackTableGateway)

        article = await cashback_table_gateway.get_cashback_article_by_id(article_id)
        combined_text = merge_messages_text(messages)

        available_articles = await cashback_table_gateway.get_in_stock_cashback_articles_by_cabinet_id(
            article.cabinet_id
        )
        # Список (id, title) для GPT
        articles_list = [(art.id, art.title) for art in available_articles]
        valid_ids = {art.id for art in available_articles}

        # Get chat history from PostgreSQL
        chat_history = []
        if buyer_id:
            chat_history = await get_chat_history(di_container, buyer_id)

        result = await openai_gateway.answer_user_question(
            user_message=combined_text,
            current_step=step_name,
            instruction_text=article.instruction_text or "",
            article_title=article.title,
            available_articles=articles_list,
            chat_history=chat_history,
        )

        response_text = result["response"]
        wants_to_stop = result["wants_to_stop"]
        switch_to_article_id = result["switch_to_article_id"]

        if buyer_id:
            await add_to_chat_history(di_container, buyer_id, combined_text, response_text)

        await bot.send_chat_action(
            chat_id=chat_id,
            action=ChatAction.TYPING,
            business_connection_id=business_connection_id,
        )
        await asyncio.sleep(DELAY_BEETWEEN_BOT_MESSAGES)

        await bot.send_message(
            chat_id=chat_id,
            text=response_text,
            business_connection_id=business_connection_id,
            parse_mode=ParseMode.MARKDOWN,
        )

        if switch_to_article_id and switch_to_article_id in valid_ids:
            await bg_manager.start(
                CashbackArticleStates.check_order,
                mode=StartMode.RESET_STACK,
                show_mode=ShowMode.SEND,
                data={"article_id": switch_to_article_id},
            )
            return

        if wants_to_stop:
            await bg_manager.done()
