from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from src.bot.states.user_flow import UserFlow
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.questions_handlers.question_flow_handler import start_buyer_flow


from src.google_sheets.google_sheets_class import GoogleSheetClass

router = Router()

@router.callback_query(F.data.startswith("subscribe_"))
async def handle_subscription(
    callback: CallbackQuery,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    CHANNEL_USERNAME: str
):
    username = callback.from_user.username or "без username"
    telegram_id = callback.from_user.id
    value = "Да" if callback.data == "subscribe_yes" else "Нет"

    spreadsheet.update_buyer_last_time_message(telegram_id=telegram_id)
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
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
                    telegram_id=telegram_id, 
                    button_name="subscribe", 
                    value="Да"
                )
                # 👉 Начинаем пошаговый диалог
                await start_buyer_flow(callback.message, spreadsheet, BUYERS_SHEET_NAME, state)
            else:
                # Не подписан
                await callback.message.answer(
                    "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                    f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                    reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
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
            reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
        )
        await state.set_state(UserFlow.waiting_for_subcription_to_channel)

    await callback.answer()