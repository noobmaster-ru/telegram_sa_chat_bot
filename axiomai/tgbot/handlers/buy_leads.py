from aiogram import Router, F
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from axiomai.infrastructure.telegram.dialogs.states import BuyLeadsStates
from axiomai.infrastructure.telegram.text import BUY_LEADS_BUTTON_TEXT

router = Router()


@router.message(F.text == BUY_LEADS_BUTTON_TEXT)
async def buy_leads_handler(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(BuyLeadsStates.waiting_for_lead_amount, mode=StartMode.RESET_STACK)
