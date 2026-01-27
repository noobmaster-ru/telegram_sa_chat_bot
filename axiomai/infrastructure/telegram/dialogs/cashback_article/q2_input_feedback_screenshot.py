import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram_dialog import inject
from redis.asyncio import Redis

from axiomai.constants import DELAY_BEETWEEN_BOT_MESSAGES
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import _update_buyer_field
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()


@inject
async def on_input_feedback_screenshot(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
    cashback_table_gateway: FromDishka[CashbackTableGateway],
    di_container: FromDishka[AsyncContainer],
    redis: FromDishka[Redis],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]
    state: FSMContext = dialog_manager.middleware_data["state"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото скриншота отзыва")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    article = await cashback_table_gateway.get_cashback_article_by_id(dialog_manager.start_data["article_id"])

    buyer_id = dialog_manager.dialog_data.get("buyer_id")

    await message.answer("⏳ Проверяю скриншот отзыва...")
    await state.set_state("skip_messaging")

    bg_manager = dialog_manager.bg()

    task = asyncio.create_task(
        _process_feedback_screenshot_background(
            bot=bot,
            redis=redis,
            bg_manager=bg_manager,
            di_container=di_container,
            openai_gateway=openai_gateway,
            photo_url=photo_url,
            article_title=article.title,
            article_brand_name=article.brand_name,
            chat_id=message.from_user.id,
            user_id=message.from_user.id,
            business_connection_id=message.business_connection_id,
            buyer_id=buyer_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _process_feedback_screenshot_background(
    bot: Bot,
    redis: Redis,
    bg_manager: DialogManager,
    di_container: AsyncContainer,
    openai_gateway: OpenAIGateway,
    photo_url: str,
    article_title: str,
    article_brand_name: str,
    chat_id: int,
    user_id: int,
    business_connection_id: str,
    buyer_id: int | None,
) -> None:
    storage = RedisStorage(redis, key_builder=DefaultKeyBuilder(with_destiny=True))
    state = FSMContext(storage, StorageKey(user_id=user_id, chat_id=chat_id, bot_id=bot.id))

    try:
        result = await openai_gateway.classify_feedback_screenshot(photo_url, article_title, article_brand_name)
    except Exception as e:
        logger.exception("classify feedback screenshot error", exc_info=e)
        await bot.send_message(
            chat_id, "Попробуйте отправить фото сюда еще раз", business_connection_id=business_connection_id
        )
        await state.set_state("client_processing")
        return

    await bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
        business_connection_id=business_connection_id,
    )
    await asyncio.sleep(DELAY_BEETWEEN_BOT_MESSAGES)

    if not result["is_feedback"]:
        cancel_reason = result["cancel_reason"]
        if cancel_reason is None:
            cancel_reason = "Попробуйте отправить фото сюда еще раз"
        await bot.send_message(
            chat_id,
            f"❌ Отзыв не найден на скриншоте\n\n<code>{cancel_reason}</code>",
            business_connection_id=business_connection_id,
        )
        await state.set_state("client_processing")
        return

    await bot.send_message(chat_id, "✅ Скриншот отзыва принят!", business_connection_id=business_connection_id)

    if buyer_id:
        await _update_buyer_field(di_container, buyer_id, is_left_feedback=True)

    await bg_manager.switch_to(CashbackArticleStates.check_labels_cut, show_mode=ShowMode.SEND)
    await state.set_state("client_processing")
