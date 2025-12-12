from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from src.core.config import constants

kb_menu = ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text=constants.SELLER_MENU_TEXT[0]), KeyboardButton(text=constants.SELLER_MENU_TEXT[1])],
	],
	resize_keyboard=True,
)

kb_add_cabinet= ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text=constants.SELLER_MENU_TEXT[0]), KeyboardButton(text=constants.SELLER_MENU_TEXT[4])],
	],
	resize_keyboard=True,
)

kb_buy_leads = ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text=constants.SELLER_MENU_TEXT[1]), KeyboardButton(text=constants.SELLER_MENU_TEXT[4])],
	],
	resize_keyboard=True,
)

kb_skip_result_json = ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text=constants.SELLER_MENU_TEXT[5]), KeyboardButton(text=constants.SELLER_MENU_TEXT[4])],
	],
	resize_keyboard=True,
)