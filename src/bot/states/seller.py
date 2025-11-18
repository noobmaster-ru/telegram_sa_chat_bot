from aiogram.fsm.state import StatesGroup, State

class SellerStates(StatesGroup):
    waiting_for_tap_to_menu = State()
    
    waiting_for_new_google_sheets_url = State()
    waiting_for_cabinet_name = State()