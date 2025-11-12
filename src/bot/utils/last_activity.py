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
    data["last_message_id"] = message.message_id
    # data["business_connection_id"]=message.business_connection_id[0],
    # data["telegram_id"]=message.from_user.id
    await state.set_data(data)