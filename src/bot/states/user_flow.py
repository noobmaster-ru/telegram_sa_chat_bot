from aiogram.fsm.state import StatesGroup, State

class UserFlow(StatesGroup):
    waiting_for_agreement = State()
    waiting_for_subcription_to_channel = State()


    waiting_for_requisites = State()
    waiting_for_bank = State()
    waiting_for_amount = State()
    waiting_for_card_or_phone_number = State()
    confirming_requisites = State()
    
    start_question_flow = State()
    waiting_for_order = State()
    waiting_for_order_receive = State()
    waiting_for_feedback = State()
    waiting_for_shk = State()