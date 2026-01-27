import asyncio
import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from dishka import AsyncContainer, FromDishka
from dishka.integrations.aiogram_dialog import inject
from redis.asyncio import Redis

from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import _update_buyer_field
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()


@inject
async def on_input_cut_labels_photo(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
    di_container: FromDishka[AsyncContainer],
    redis: FromDishka[Redis],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]
    state: FSMContext = dialog_manager.middleware_data["state"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото разрезанных этикеток")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    buyer_id = dialog_manager.dialog_data.get("buyer_id")

    await message.answer("⏳ Проверяю фотографию разрезанных этикеток...")
    await state.set_state("skip_messaging")

    bg_manager = dialog_manager.bg()
    task = asyncio.create_task(
        _process_cut_labels_photo_background(
            bot=bot,
            redis=redis,
            bg_manager=bg_manager,
            di_container=di_container,
            openai_gateway=openai_gateway,
            photo_url=photo_url,
            chat_id=message.from_user.id,
            user_id=message.from_user.id,
            business_connection_id=message.business_connection_id,
            buyer_id=buyer_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _process_cut_labels_photo_background(
    bot: Bot,
    redis: Redis,
    bg_manager: DialogManager,
    di_container: AsyncContainer,
    openai_gateway: OpenAIGateway,
    photo_url: str,
    chat_id: int,
    user_id: int,
    business_connection_id: str,
    buyer_id: int | None,
) -> None:
    storage = RedisStorage(redis, key_builder=DefaultKeyBuilder(with_destiny=True))
    state = FSMContext(storage, StorageKey(user_id=user_id, chat_id=chat_id, bot_id=bot.id))

    try:
        result = await openai_gateway.classify_cut_labels_photo(photo_url)
    except Exception as e:
        logger.exception("classify cut labels photo error", exc_info=e)
        await bot.send_message(
            chat_id, "Попробуйте отправить фото сюда еще раз", business_connection_id=business_connection_id
        )
        await state.set_state("client_processing")
        return

    if not result["is_cut_labels"]:
        cancel_reason = result["cancel_reason"]
        if cancel_reason is None:
            cancel_reason = "Попробуйте разрезать этикетки еще раз и отправите фото сюда"
        await bot.send_message(
            chat_id,
            f"❌ Фото разрезанных штрихкодов не принято\n\n<code>{cancel_reason}</code>",
            business_connection_id=business_connection_id,
        )
        await state.set_state("client_processing")
        return

    await bot.send_message(
        chat_id, "✅ Фотография разрезанных этикеток принята!", business_connection_id=business_connection_id
    )
    await bot.send_message(
        chat_id,
        "☺ Вы прислали все фотографии, которые были нам нужны. Спасибо!",
        business_connection_id=business_connection_id,
    )

    if buyer_id:
        await _update_buyer_field(di_container, buyer_id, is_cut_labels=True)

    await bg_manager.switch_to(CashbackArticleStates.input_requisites, show_mode=ShowMode.SEND)
    await state.set_state("client_processing")
