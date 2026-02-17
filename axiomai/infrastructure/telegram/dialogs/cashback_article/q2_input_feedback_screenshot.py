import asyncio
import json
import logging
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.config import Config
from axiomai.infrastructure.chat_history import add_to_chat_history
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.message_debouncer import MessageData, MessageDebouncer
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import (
    build_articles_for_gpt,
    get_pending_nm_ids_for_step,
)
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates

logger = logging.getLogger(__name__)


@inject
async def on_input_feedback_screenshot(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
    di_container: FromDishka[AsyncContainer],
    message_debouncer: FromDishka[MessageDebouncer],
    config: FromDishka[Config],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото скриншота отзыва")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    message_data = MessageData(
        text=message.caption,
        timestamp=datetime.now(UTC).timestamp(),
        message_id=message.message_id,
        has_photo=bool(message.photo),
        photo_url=photo_url,
    )

    bg_manager = dialog_manager.bg()
    app_container = di_container.parent_container

    await message_debouncer.add_message(
        business_connection_id=message.business_connection_id,
        chat_id=message.chat.id,
        message_data=message_data,
        process_callback=lambda biz_id, chat_id, msgs: _process_feedback_screenshot_background(
            messages=msgs,
            bot=bot,
            bg_manager=bg_manager,
            di_container=app_container,
            openai_gateway=openai_gateway,
            config=config,
            chat_id=chat_id,
            business_connection_id=biz_id,
        ),
    )


async def _process_feedback_screenshot_background(
    messages: list[MessageData],
    bot: Bot,
    bg_manager: DialogManager,
    di_container: AsyncContainer,
    openai_gateway: OpenAIGateway,
    config: Config,
    chat_id: int,
    business_connection_id: str,
) -> None:
    photo_urls = [msg.photo_url for msg in messages if msg.photo_url]

    if len(photo_urls) > 1:
        await bot.send_message(
            chat_id,
            "Пожалуйста, отправьте только один скриншот отзыва. Я получил несколько фото, и не могу понять, какое из них правильное.",
            business_connection_id=business_connection_id,
        )
        return

    photo_url = photo_urls[0]

    await bot.send_message(chat_id, "⏳ Проверяю скриншот отзыва...", business_connection_id=business_connection_id)

    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        cabinet_gateway = await r_container.get(CabinetGateway)
        cashback_table_gateway = await r_container.get(CashbackTableGateway)

        cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(business_connection_id)
        buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(chat_id, cabinet.id)
        articles = await cashback_table_gateway.get_cashback_articles_by_nm_ids([b.nm_id for b in buyers])

    pending_nm_ids = get_pending_nm_ids_for_step(buyers, step="check_received")
    pending_articles = [a for a in articles if a.nm_id in pending_nm_ids]
    articles_for_gpt = build_articles_for_gpt(pending_articles)

    result = None
    try:
        result = await openai_gateway.classify_feedback_screenshot(
            photo_url=photo_url,
            articles=articles_for_gpt,
        )
    except Exception as e:
        logger.exception("classify feedback screenshot error", exc_info=e)
        await bot.send_message(
            chat_id, "Попробуйте отправить фото сюда еще раз", business_connection_id=business_connection_id
        )
        result = "classify feedback screenshot error"
        return
    finally:
        await add_to_chat_history(di_container, chat_id, cabinet.id, "[Скрин отзыва]", json.dumps(result))

    await bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(config.delay_between_bot_messages)

    if not result["is_feedback"] or not result["nm_id"]:
        cancel_reason = result["cancel_reason"]
        if cancel_reason is None:
            cancel_reason = "Попробуйте отправить фото сюда еще раз"
        await bot.send_message(
            chat_id,
            f"❌ Отзыв не найден на скриншоте\n\n<code>{cancel_reason}</code>",
            business_connection_id=business_connection_id,
        )
        return

    buyer_id = next((b.id for b in buyers if b.nm_id == result["nm_id"]), None)
    if not buyer_id:
        logger.error("buyer not found for nm_id %s, chat_id %s", result["nm_id"], chat_id)
        return

    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        transaction_manager = await r_container.get(TransactionManager)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        buyer.is_left_feedback = True
        await transaction_manager.commit()

        buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(chat_id, cabinet.id)

    article = next((a for a in articles if a.nm_id == result["nm_id"]), None)

    if not article:
        raise ValueError(f"Article in result {result["nm_id"]} not found in {pending_nm_ids}")

    await bot.send_message(
        chat_id,
        f"✅ Скриншот отзыва для <b>{article.title}</b> принят!",
        business_connection_id=business_connection_id,
    )

    pending_feedback = get_pending_nm_ids_for_step(buyers, "check_received")
    if pending_feedback:
        await bg_manager.switch_to(CashbackArticleStates.check_received, show_mode=ShowMode.SEND)
    else:
        await bg_manager.switch_to(CashbackArticleStates.check_labels_cut, show_mode=ShowMode.SEND)
