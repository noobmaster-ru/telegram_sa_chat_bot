from contextlib import suppress

from aiogram import F, Router
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.cabinet import CabinetAlreadyExistsError
from axiomai.application.interactors.create_cabinet import CreateCabinet
from axiomai.infrastructure.telegram.dialogs.states import CreateCashbackTableStates
from axiomai.infrastructure.telegram.text import ADD_CABINET_BUTTON_TEXT

router = Router()


@router.message(F.text == ADD_CABINET_BUTTON_TEXT)
@inject
async def add_cabinet_handler(
    message: Message, dialog_manager: DialogManager, create_cabinet: FromDishka[CreateCabinet]
) -> None:
    with suppress(CabinetAlreadyExistsError):
        await create_cabinet.execute(telegram_id=message.from_user.id)

    await dialog_manager.start(CreateCashbackTableStates.copy_gs_template, mode=StartMode.RESET_STACK)
