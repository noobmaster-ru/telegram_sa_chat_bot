from aiogram.fsm.state import StatesGroup, State

class SellerStates(StatesGroup):
    waiting_for_tap_to_menu = State()
    
    waiting_for_new_google_sheets_url = State()
    waiting_for_tap_to_keyboard_gs = State()
    
    waiting_for_brand_name = State()
    waiting_for_tap_to_keyboard_brand_name = State()
    
    add_cabinet_to_db = State()
     
    waiting_for_nm_id = State()
    waiting_for_nm_id_amount = State()
    waiting_for_nm_id_photo = State()