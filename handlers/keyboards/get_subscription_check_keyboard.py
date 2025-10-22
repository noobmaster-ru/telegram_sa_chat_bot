from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_subscription_check_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подписался", callback_data="subscribe_yes"),
            InlineKeyboardButton(text="❌ Не подписался", callback_data="subscribe_no")
        ]
    ])
    return keyboard