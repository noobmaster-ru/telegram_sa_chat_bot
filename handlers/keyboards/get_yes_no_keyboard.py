from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === Клавиатура Да / Нет ===
def get_yes_no_keyboard(callback_prefix: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"{callback_prefix}_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{callback_prefix}_no")
        ]
    ])