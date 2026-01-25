from aiogram.fsm.state import StatesGroup, State


class CreateCashbackTableStates(StatesGroup):
    copy_gs_template = State()


class MyCabinetStates(StatesGroup):
    select_option = State()


class BuyLeadsStates(StatesGroup):
    waiting_for_lead_amount = State()
    waiting_for_payment_confirm_click = State()


class CashbackArticleStates(StatesGroup):
    show_instruction = State()
    agreement_terms = State()
    check_order = State()
    check_received = State()
    check_labels_cut = State()
