from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_payment_admin_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить оплату",
                    callback_data=f"admin_pay_ok:{payment_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить оплату",
                    callback_data=f"admin_pay_fail:{payment_id}",
                ),
            ]
        ]
    )


# === Клавиатура Да / Нет ===
def get_yes_no_keyboard(callback_prefix: str, statement: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ Да, {statement}", callback_data=f"{callback_prefix}_yes"),
            InlineKeyboardButton(text=f"❌ Не {statement}", callback_data=f"{callback_prefix}_no")
        ]
    ])