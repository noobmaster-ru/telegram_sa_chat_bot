from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

def get_three_buttons_keyboard() -> InlineKeyboardMarkup:
    """Создаёт клавиатуру с тремя вопросами и кнопками Да/Нет"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Заказ сделан", callback_data="order_yes"),
        ],
        [
            InlineKeyboardButton(text="✅ Отзыв оставлен", callback_data="feedback_yes"),
        ],
        [
            InlineKeyboardButton(text="✅ ШК разрезаны", callback_data="shk_yes"),
        ]
    ])
    return keyboard


def get_different_number_of_buttons_keyboard(list_of_need_buttons: list) -> InlineKeyboardMarkup:
    "list_of_need_buttons = ['feedback', 'order', 'shk']"
    """Создаёт клавиатуру с двумя вопросами и кнопками Да/Нет"""
    list_for_inline_keyboard = []
    for elem in list_of_need_buttons:
        if elem == "feedback":
            list_for_inline_keyboard.append([
                InlineKeyboardButton(text="✅ Отзыв оставлен", callback_data="feedback_yes"),
            ])
        elif elem == "order":
            list_for_inline_keyboard.append([
                InlineKeyboardButton(text="✅ Заказ сделан", callback_data="order_yes"),
            ])
        elif elem == "shk":
            list_for_inline_keyboard.append([
                InlineKeyboardButton(text="✅ ШК разрезаны", callback_data="shk_yes"),
            ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=list_for_inline_keyboard)
    return keyboard