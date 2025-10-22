from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from google_sheets.google_sheets_class import GoogleSheetClass

# from handlers.keyboards.keyboards import get_subscription_check_keyboard

from handlers.keyboards.get_subscription_check_keyboard import get_subscription_check_keyboard
from handlers.question_flow import start_buyer_flow

router = Router()

@router.callback_query(F.data.startswith("subscribe_"))
async def handle_subscription(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    CHANNEL_USERNAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "subscribe_yes" else "Нет"

    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        username=username,
        button_name="subscribe",
        value=value
    )

    if callback.data == "subscribe_yes":
        # Проверяем подписку
        try:
            member = await callback.message.bot.get_chat_member(
                chat_id=CHANNEL_USERNAME,
                user_id=callback.from_user.id
            )
            if member.status in ("member", "administrator", "creator"):
                # Пользователь подписан → продолжаем
                await callback.message.answer(
                    "✅ Отлично! Вы подписаны на канал.",
                )

                # обновляем статус в таблице
                spreadsheet.update_buyer_button_status(
                    sheet_name=BUYERS_SHEET_NAME, 
                    username=username, 
                    button_name="subscribe", 
                    value="Да"
                )
                # 👉 Начинаем пошаговый диалог
                await start_buyer_flow(callback.message, spreadsheet, BUYERS_SHEET_NAME)
            else:
                # Не подписан
                await callback.message.answer(
                    "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                    f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                    reply_markup=get_subscription_check_keyboard()
                )
        except TelegramBadRequest:
            await callback.message.answer(
                "⚠️ Не удалось проверить подписку. Проверьте, что бот — администратор канала."
            )
    else:
        # Не подписан
        await callback.message.answer(
            "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
            f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
            reply_markup=get_subscription_check_keyboard()
        )

    await callback.answer()