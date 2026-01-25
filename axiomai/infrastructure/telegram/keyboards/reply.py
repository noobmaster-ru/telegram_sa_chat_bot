from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from axiomai.infrastructure.telegram.text import (
    ADD_CABINET_BUTTON_TEXT,
    SUPPORT_BUTTON_TEXT,
    BUY_LEADS_BUTTON_TEXT,
    MY_CABINET_BUTTON_TEXT,
)

kb_add_cabinet = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=ADD_CABINET_BUTTON_TEXT), KeyboardButton(text=SUPPORT_BUTTON_TEXT)],
    ],
    resize_keyboard=True,
)


kb_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BUY_LEADS_BUTTON_TEXT), KeyboardButton(text=SUPPORT_BUTTON_TEXT)],
        [KeyboardButton(text=MY_CABINET_BUTTON_TEXT)],
    ],
    resize_keyboard=True,
)
