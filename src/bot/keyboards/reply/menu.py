from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from src.core.config import constants

kb_menu = ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text=constants.SELLER_MENU_TEXT[0]), KeyboardButton(text=constants.SELLER_MENU_TEXT[1])],
	[KeyboardButton(text=constants.SELLER_MENU_TEXT[2]), KeyboardButton(text=constants.SELLER_MENU_TEXT[3])]
	],
	resize_keyboard=True,
)
