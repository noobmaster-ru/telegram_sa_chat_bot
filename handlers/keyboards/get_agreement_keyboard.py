from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_agreement_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="agree_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="agree_no"),
        ]
    ])
    return keyboard