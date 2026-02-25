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
from axiomai.infrastructure.message_debouncer import MessageData, MessageDebouncer, TaskStrategy
from axiomai.infrastructure.openai import ClassifyCutLabelsResult, OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import get_pending_nm_ids_for_step
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates

logger = logging.getLogger(__name__)


@inject
async def on_input_cut_labels_photo(
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
        await message.answer("Пожалуйста, отправьте фото разрезанных этикеток")
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
        process_callback=lambda biz_id, chat_id, msgs: _process_cut_labels_photo_background(
            messages=msgs,
            bot=bot,
            bg_manager=bg_manager,
            di_container=app_container,
            openai_gateway=openai_gateway,
            config=config,
            chat_id=chat_id,
            business_connection_id=biz_id,
        ),
        strategy=TaskStrategy.PHOTO_ONLY
    )


async def _process_cut_labels_photo_background(
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
            "Пожалуйста, отправьте по одной фотографию разрезанных этикеток. "
            "Я получил несколько фото, и не могу понять, какое из них правильное.",
            business_connection_id=business_connection_id,
        )
        return

    photo_url = photo_urls[0]

    await bot.send_message(
        chat_id, "⏳ Проверяю фотографию разрезанных этикеток...", business_connection_id=business_connection_id
    )

    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        cabinet_gateway = await r_container.get(CabinetGateway)
        cashback_table_gateway = await r_container.get(CashbackTableGateway)

        cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(business_connection_id)
        buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(chat_id, cabinet.id)
        articles = await cashback_table_gateway.get_cashback_articles_by_nm_ids([b.nm_id for b in buyers])

    pending_nm_ids = get_pending_nm_ids_for_step(buyers, step="check_labels_cut")
    pending_articles = [a for a in articles if a.nm_id in pending_nm_ids]

    result: str | None | ClassifyCutLabelsResult = None
    try:
        result = await openai_gateway.classify_cut_labels_photo(photo_url, pending_articles)
    except Exception as e:
        logger.exception("classify cut labels photo error", exc_info=e)
        await bot.send_message(
            chat_id, "Попробуйте отправить фото сюда еще раз", business_connection_id=business_connection_id
        )
        result = "classify cut labels photo error"
        return
    finally:
        await add_to_chat_history(di_container, chat_id, cabinet.id, "[Скрин этикеток]", json.dumps(result))

    await bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(config.delay_between_bot_messages)

    if not result["is_cut_labels"]:
        cancel_reason = result["cancel_reason"]
        if cancel_reason is None:
            cancel_reason = "Попробуйте разрезать этикетки еще раз и отправите фото сюда"
        await bot.send_message(
            chat_id,
            f"❌ Фото разрезанных штрихкодов не принято\n\n<code>{cancel_reason}</code>",
            business_connection_id=business_connection_id,
        )
        return

    buyer_id = next((b.id for b in buyers if b.nm_id in pending_nm_ids), None)

    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        transaction_manager = await r_container.get(TransactionManager)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        buyer.is_cut_labels = True
        await transaction_manager.commit()

        buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(chat_id, cabinet.id)

    article = next((a for a in pending_articles), None)

    if not article:
        raise ValueError(f"Pending articles is empty for user {chat_id}")

    await bot.send_message(
        chat_id,
        f"✅ Фотография разрезанных этикеток для <b>{article.title}</b> принята!",
        business_connection_id=business_connection_id,
    )

    pending_cut_labels = get_pending_nm_ids_for_step(buyers, "check_labels_cut")
    if pending_cut_labels:
        await bg_manager.switch_to(CashbackArticleStates.check_labels_cut, show_mode=ShowMode.SEND)
    else:
        await bot.send_message(
            chat_id,
            "☺ Вы прислали все фотографии, которые были нам нужны. Спасибо!",
            business_connection_id=business_connection_id,
        )
        await bg_manager.switch_to(CashbackArticleStates.input_requisites, show_mode=ShowMode.SEND)
