from aiogram import Router, F
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from axiomai.infrastructure.telegram.dialogs.states import RefillBalanceStates
from axiomai.infrastructure.telegram.text import REFILL_BALANCE_BUTTON_TEXT

router = Router()


@router.message(F.text == REFILL_BALANCE_BUTTON_TEXT)
async def refill_balance_handler(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(RefillBalanceStates.waiting_for_amount, mode=StartMode.RESET_STACK)
