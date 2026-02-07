from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from axiomai.infrastructure.database.models import Cabinet
from axiomai.infrastructure.telegram.text import (
    ADD_CABINET_BUTTON_TEXT,
    BUY_LEADS_BUTTON_TEXT,
    MY_CABINET_BUTTON_TEXT,
    REFILL_BALANCE_BUTTON_TEXT,
    SUPPORT_BUTTON_TEXT,
)

kb_add_cabinet = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADD_CABINET_BUTTON_TEXT), KeyboardButton(text=SUPPORT_BUTTON_TEXT)],
    ],
    resize_keyboard=True,
)


def get_kb_menu(cabinet: Cabinet) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    if cabinet.is_superbanking_connect:
        builder.row(KeyboardButton(text=BUY_LEADS_BUTTON_TEXT), KeyboardButton(text=REFILL_BALANCE_BUTTON_TEXT))
    else:
        builder.row(KeyboardButton(text=BUY_LEADS_BUTTON_TEXT))

    builder.row(KeyboardButton(text=MY_CABINET_BUTTON_TEXT), KeyboardButton(text=SUPPORT_BUTTON_TEXT))

    return builder.as_markup(resize_keyboard=True)
