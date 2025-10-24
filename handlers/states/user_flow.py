from aiogram.fsm.state import StatesGroup, State

class UserFlow(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_order = State()
    waiting_for_order_receive = State()
    waiting_for_feedback = State()
    waiting_for_shk = State()