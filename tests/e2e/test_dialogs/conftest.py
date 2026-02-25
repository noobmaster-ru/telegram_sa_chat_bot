from copy import deepcopy
from datetime import datetime
from typing import Any, Optional, Union

import pytest
from aiogram import Dispatcher, Bot, Router
from aiogram.fsm.storage.base import BaseStorage
from aiogram.methods import (
    TelegramMethod,
    AnswerCallbackQuery,
    DeleteBusinessMessages,
    SendMessage,
    ReadBusinessMessage,
    SendChatAction,
    GetFile,
    EditMessageText,
)
from aiogram.types import Message, Update, PhotoSize, File, ReplyKeyboardMarkup
from aiogram_dialog import setup_dialogs, BaseDialogManager, UnsetId, ChatEvent, DialogManager, ShowMode
from aiogram_dialog.api.entities import NewMessage, OldMessage
from aiogram_dialog.api.internal import DialogManagerFactory
from aiogram_dialog.api.protocols import (
    MessageManagerProtocol,
    MediaIdStorageProtocol,
    DialogRegistryProtocol,
    MessageNotModified,
)
from aiogram_dialog.context.media_storage import MediaIdStorage
from aiogram_dialog.manager.manager import ManagerImpl
from aiogram_dialog.test_tools import MockMessageManager, BotClient
from aiogram_dialog.test_tools.mock_message_manager import MEDIA_CLASSES, file_id, file_unique_id
from dishka.integrations.aiogram import setup_dishka

from axiomai.infrastructure.telegram import dialogs
from axiomai.tgbot import handlers


class FakeBot(Bot):
    def __init__(self) -> None:
        self.sent_messages: list[SendMessage] = []
        self.deleted_business_messages: list[DeleteBusinessMessages] = []
        self.__token = "FAKE_BOT_TOKEN"

    @property
    def token(self) -> str:
        return self.__token

    @property
    def id(self):
        return 1

    async def __call__(self, method: TelegramMethod[Any], request_timeout: int | None = None) -> Any:
        del request_timeout  # unused
        if isinstance(method, (EditMessageText, AnswerCallbackQuery, ReadBusinessMessage, SendChatAction, DeleteBusinessMessages)):
            if isinstance(method, DeleteBusinessMessages):
                self.deleted_business_messages.append(method)
            return True
        if isinstance(method, SendMessage):
            self.sent_messages.append(method)
            return True
        if isinstance(method, GetFile):
            return File(file_id="fake_file_id", file_unique_id="unique_fake_file_id", file_path="path/to/fake/file")

        raise RuntimeError("Fake bot should not be used to call telegram")

    def __hash__(self) -> int:
        return 1

    def __eq__(self, other) -> bool:
        return self is other


class FakeBotClient(BotClient):
    def __init__(
        self,
        dp: Dispatcher,
        user_id: int = 1,
        chat_id: int = 1,
        business_connection_id: str = "_fUur5pbmEsVFQAAmQjYqSx73vk",
        chat_type: str = "private",
        bot: Bot | None = None,
    ) -> None:
        self.business_connection_id = business_connection_id
        super().__init__(dp, user_id, chat_id, chat_type, bot)

    def _new_business_message(self, text: str, reply_to: Message | None):
        return Message(
            message_id=self._new_message_id(),
            date=datetime.fromtimestamp(1234567890),
            chat=self.chat,
            from_user=self.user,
            text=text,
            reply_to_message=reply_to,
            business_connection_id=self.business_connection_id,
        )

    def _new_business_photo_message(self):
        return Message(
            message_id=self._new_message_id(),
            date=datetime.fromtimestamp(1234567890),
            chat=self.chat,
            from_user=self.user,
            photo=[
                PhotoSize(
                    file_id="fake_file_id", file_unique_id="unique_fake_file_id", width=800, height=600, file_size=12345
                )
            ],
            business_connection_id=self.business_connection_id,
        )

    async def send_business(self, text: str, reply_to: Message | None = None):
        return await self.dp.feed_update(
            self.bot,
            Update(
                update_id=self._new_update_id(),
                business_message=self._new_business_message(text, reply_to),
            ),
        )

    async def send_business_photo(self):
        return await self.dp.feed_update(
            self.bot,
            Update(
                update_id=self._new_update_id(),
                business_message=self._new_business_photo_message(),
            ),
        )


class FakeManager(ManagerImpl):
    def bg(
        self,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        stack_id: Optional[str] = None,
        thread_id: Union[int, None, UnsetId] = UnsetId.UNSET,
        business_connection_id: Union[str, None, UnsetId] = UnsetId.UNSET,
        load: bool = False,
    ) -> BaseDialogManager:
        return self


class FakeDialogManagerFactory(DialogManagerFactory):
    def __init__(
        self,
        message_manager: MessageManagerProtocol,
        media_id_storage: MediaIdStorageProtocol,
    ) -> None:
        self.message_manager = message_manager
        self.media_id_storage = media_id_storage

    def __call__(
        self,
        event: ChatEvent,
        data: dict,
        registry: DialogRegistryProtocol,
        router: Router,
    ) -> DialogManager:
        return FakeManager(
            event=event,
            data=data,
            message_manager=self.message_manager,
            media_id_storage=self.media_id_storage,
            registry=registry,
            router=router,
        )


class FakeMessageManager(MockMessageManager):
    async def show_message(self, bot: Bot, new_message: NewMessage, old_message: Optional[OldMessage]) -> OldMessage:
        assert isinstance(new_message, NewMessage)
        assert isinstance(old_message, (OldMessage, type(None)))
        if new_message.show_mode is ShowMode.NO_UPDATE:
            raise MessageNotModified

        message_id = self.last_message_id + 1
        self.last_message_id = message_id

        if new_message.media:
            contents = {
                "caption": new_message.text,
                new_message.media.type: MEDIA_CLASSES[new_message.media.type](
                    new_message.media,
                ),
            }
        else:
            contents = {
                "text": new_message.text,
            }

        message = Message(
            message_id=message_id,
            date=datetime.now(),
            chat=new_message.chat,
            reply_markup=deepcopy(new_message.reply_markup),
            business_connection_id=new_message.business_connection_id,
            **contents,
        )
        self.sent_messages.append(message)

        return OldMessage(
            message_id=message_id,
            chat=new_message.chat,
            text=new_message.text,
            media_id=(file_id(new_message.media) if new_message.media else None),
            media_uniq_id=(file_unique_id(new_message.media) if new_message.media else None),
            has_reply_keyboard=isinstance(
                new_message.reply_markup,
                ReplyKeyboardMarkup,
            ),
            business_connection_id=None,
        )


@pytest.fixture()
async def message_manager():
    return FakeMessageManager()


@pytest.fixture()
async def fake_bot():
    return FakeBot()


@pytest.fixture()
async def bot_client(di_container, message_manager, fake_bot):
    storage = await di_container.get(BaseStorage)
    dp = Dispatcher(storage=storage)

    handlers.setup(dp)
    dialogs.setup(dp)

    client = FakeBotClient(dp, bot=fake_bot)

    setup_dialogs(
        dp,
        dialog_manager_factory=FakeDialogManagerFactory(
            message_manager=message_manager, media_id_storage=MediaIdStorage()
        ),
    )
    setup_dishka(di_container, dp)

    yield client

    for r in dp.sub_routers:
        cleanup_routers(r)


def cleanup_routers(router: Router | None):
    if not router:
        return
    if not router._parent_router:
        return

    router._parent_router = None
    for r in router.sub_routers:
        cleanup_routers(r)
