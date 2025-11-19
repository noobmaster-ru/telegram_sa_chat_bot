from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.core.config import constants

def get_sub_to_channel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Подписаться на канал", url=f"https://t.me/{constants.CHANNEL_USERNAME_STR}")]
        ]
    )
