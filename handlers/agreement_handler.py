from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from google_sheets.google_sheets_class import GoogleSheetClass
from aiogram.fsm.context import FSMContext

from handlers.keyboards.get_subscription_check_keyboard import get_subscription_check_keyboard
from handlers.keyboards.get_agreement_keyboard import get_agreement_keyboard

from handlers.questions_handlers.question_flow_handler import start_buyer_flow

from handlers.states.user_flow import UserFlow
router = Router()

@router.callback_query(F.data.startswith("agree_"))
async def handle_agreement(
    callback: CallbackQuery,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    CHANNEL_USERNAME: str,
):
    username = callback.from_user.username or "без username"
    telegram_id = callback.from_user.id
    value = "Да" if callback.data == "agree_yes" else "Нет"

    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        telegram_id=telegram_id,
        button_name="agree",
        value=value
    )

    if callback.data == "agree_yes":
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
                    reply_markup=get_subscription_check_keyboard()
                )
        except TelegramBadRequest:
            await callback.message.answer(
                "⚠️ Не удалось проверить подписку. Проверьте, что бот — администратор канала."
            )
    else:
        await callback.message.answer(
            "❌ Без согласия участие невозможно. Вы согласны на условия?",
            reply_markup=get_agreement_keyboard()
        )
        await state.set_state(UserFlow.waiting_for_agreement)

    await callback.answer()