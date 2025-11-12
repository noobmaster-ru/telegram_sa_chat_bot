import time
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

async def update_last_activity(
    state: FSMContext,
    message: Message
):
    """Сохраняет timestamp последнего действия пользователя"""
    data = await state.get_data()
    data["last_time_activity"] = time.time()
    data["last_messages_ids"].append(message.message_id)
    await state.set_data(data)