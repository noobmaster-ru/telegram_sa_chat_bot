import asyncio
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
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.message_debouncer import MessageData, MessageDebouncer
from axiomai.infrastructure.openai import OpenAIGateway
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

    buyer_id = dialog_manager.dialog_data.get("buyer_id")

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
            buyer_id=buyer_id,
        ),
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
    buyer_id: int | None,
) -> None:
    photo_urls = [msg.photo_url for msg in messages if msg.photo_url]

    if len(photo_urls) > 1:
        await bot.send_message(
            chat_id,
            "Пожалуйста, отправьте только одну фотографию разрезанных этикеток. "
            "Я получил несколько фото, и не могу понять, какое из них правильное.",
            business_connection_id=business_connection_id,
        )
        return

    photo_url = photo_urls[0]

    await bot.send_message(
        chat_id, "⏳ Проверяю фотографию разрезанных этикеток...", business_connection_id=business_connection_id
    )

    try:
        result = await openai_gateway.classify_cut_labels_photo(photo_url)
    except Exception as e:
        logger.exception("classify cut labels photo error", exc_info=e)
        await bot.send_message(
            chat_id, "Попробуйте отправить фото сюда еще раз", business_connection_id=business_connection_id
        )
        return

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

    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        transaction_manager = await r_container.get(TransactionManager)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        buyer.is_cut_labels = True
        await transaction_manager.commit()

    await bot.send_message(
        chat_id, "✅ Фотография разрезанных этикеток принята!", business_connection_id=business_connection_id
    )
    await bot.send_message(
        chat_id,
        "☺ Вы прислали все фотографии, которые были нам нужны. Спасибо!",
        business_connection_id=business_connection_id,
    )

    await bg_manager.switch_to(CashbackArticleStates.input_requisites, show_mode=ShowMode.SEND)
