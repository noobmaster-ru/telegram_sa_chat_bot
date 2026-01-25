from aiogram import Router, F
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from axiomai.infrastructure.telegram.dialogs.states import MyCabinetStates
from axiomai.infrastructure.telegram.text import MY_CABINET_BUTTON_TEXT

router = Router()


@router.message(F.text == MY_CABINET_BUTTON_TEXT)
async def my_cabinet_handler(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(MyCabinetStates.select_option, mode=StartMode.RESET_STACK)
