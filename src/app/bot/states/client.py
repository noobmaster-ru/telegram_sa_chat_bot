from aiogram.fsm.state import StatesGroup, State

class ClientStates(StatesGroup):
    # user flow start
    waiting_for_agreement = State()
    # waiting_for_subcription_to_channel = State()
    waiting_for_order = State()

    # photo of order
    waiting_for_photo_order = State()
    waiting_for_order_receive = State()
    waiting_for_feedback = State()
    
    # photo of feedback
    waiting_for_photo_feedback = State()
    waiting_for_shk = State()
    
    # photo of shk
    waiting_for_photo_shk = State()
    waiting_for_requisites = State()
    

    waiting_for_bank = State()
    waiting_for_amount = State()
    waiting_for_card_or_phone_number = State()
    confirming_requisites = State()
    
    # start_question_flow = State()
    continue_dialog = State()