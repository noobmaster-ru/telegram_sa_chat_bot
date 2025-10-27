from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.google_sheets.google_sheets_class import GoogleSheetClass

from src.bot.questions_handlers.question_product_ordered_handler import ask_is_product_ordered_question

# # === Старт последовательных вопросов ===
async def start_buyer_flow(
    message: Message, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str,
    state: FSMContext
):

    # Начинаем с первого вопроса
    await ask_is_product_ordered_question(message, state)