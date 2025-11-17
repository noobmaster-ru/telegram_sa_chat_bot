from aiogram.fsm.state import StatesGroup, State

class SellerStates(StatesGroup):
    google_sheet_handler = State()
    service_account_handler = State()
    # result_json = State()
    nm_id_photo = State()
    parsing_data = State()