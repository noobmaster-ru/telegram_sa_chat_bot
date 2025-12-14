from aiogram.fsm.state import StatesGroup, State

class SellerStates(StatesGroup):
    email = State()
    waiting_for_tap_to_keyboard_email = State()
    
    waiting_for_tap_to_menu = State()
    
    waiting_for_organization_name = State()
    waiting_for_tap_to_keyboard_org_name = State()
    
    waiting_for_new_google_sheets_url = State()
    waiting_for_tap_to_keyboard_gs = State()
    
    waiting_for_business_account_id = State()
    waiting_for_tap_to_keyboard_bus_acc_id = State()
    
    
    waiting_for_link_bot_to_bus_acc = State()
    
    waiting_for_business_connection_id = State()
    waiting_result_json = State()
    waiting_for_tap_to_keyboard_result_json = State()
    
    add_cabinet_to_db = State()
     
    waiting_for_nm_id = State()
    waiting_for_nm_id_name = State()
    waiting_for_nm_id_photo = State()
    
    waiting_for_delete_confirmation = State()
    
    # Новые состояния для оплаты
    waiting_for_leads = State()
    waiting_for_leads_amount = State()
    waiting_for_payment_confirm_click = State()
    
    