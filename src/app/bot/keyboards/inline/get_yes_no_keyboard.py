# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# # === Клавиатура Да / Нет ===
# def get_yes_no_keyboard(callback_prefix: str, statement: str) -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [
#             InlineKeyboardButton(text=f"✅ Да, {statement}", callback_data=f"{callback_prefix}_yes"),
#             InlineKeyboardButton(text=f"❌ Не {statement}", callback_data=f"{callback_prefix}_no")
#         ]
#     ])