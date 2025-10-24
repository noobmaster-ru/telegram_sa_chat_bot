from handlers.states.user_flow import UserFlow
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram import Router, types

from handlers.states.user_flow import UserFlow
from google_sheets.google_sheets_class import GoogleSheetClass

router = Router()
# Этот обработчик сработает, если пользователь напишет текст,
# пока бот ждёт нажатие кнопки в любом из заданных состояний.
@router.business_message(
    StateFilter(
        UserFlow.waiting_for_agreement,
        UserFlow.waiting_for_order,
        UserFlow.waiting_for_order_receive,
        UserFlow.waiting_for_feedback,
        UserFlow.waiting_for_shk,
    )
)
async def handle_unexpected_text(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    telegram_id = message.from_user.id
    # обновляем время последнего сообщения
    spreadsheet.update_buyer_last_time_message(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id
    )
    await message.answer("Пожалуйста, используйте кнопки для ответа.")