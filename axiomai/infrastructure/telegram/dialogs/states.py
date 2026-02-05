from aiogram.fsm.state import State, StatesGroup


class CreateCashbackTableStates(StatesGroup):
    copy_gs_template = State()
    ask_superbanking = State()


class MyCabinetStates(StatesGroup):
    select_option = State()


class BuyLeadsStates(StatesGroup):
    waiting_for_lead_amount = State()
    waiting_for_payment_confirm_click = State()


class CashbackArticleStates(StatesGroup):
    check_order = State()
    check_received = State()
    check_labels_cut = State()
    input_requisites = State()
