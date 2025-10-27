from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.questions_handlers.question_product_ordered_handler import ask_is_product_ordered_question

# # === Старт последовательных вопросов ===
async def start_buyer_flow(
    message: Message, 
    state: FSMContext
):

    # Начинаем с первого вопроса
    await ask_is_product_ordered_question(message, state)