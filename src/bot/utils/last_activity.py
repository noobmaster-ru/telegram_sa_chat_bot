from aiogram.fsm.context import FSMContext
import time

async def update_last_activity(state: FSMContext):
    """Сохраняет timestamp последнего действия пользователя"""
    data = await state.get_data()
    data["last_time_activity"] = time.time()
    await state.set_data(data)