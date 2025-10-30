from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from src.bot.states.user_flow import UserFlow
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard



from src.services.google_sheets_class import GoogleSheetClass

router = Router()

@router.callback_query(F.data.startswith("subscribe_"))
async def handle_subscription(
    callback: CallbackQuery,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    CHANNEL_USERNAME: str,
    nm_id: str
):
    telegram_id = callback.from_user.id
    value = "Да" if callback.data == "subscribe_yes" else "Нет"

    await spreadsheet.update_buyer_button_status(
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
                await callback.message.edit_text(
                    "✅ Отлично! Вы подписаны на канал.",
                )

                # обновляем статус в таблице
                await spreadsheet.update_buyer_button_status(
                    sheet_name=BUYERS_SHEET_NAME, 
                    telegram_id=telegram_id, 
                    button_name="subscribe", 
                    value="Да"
                )
                # 👉 Начинаем пошаговый диалог
                await callback.message.edit_text(
                    f"📦 Вы заказали товар {nm_id}?", 
                    reply_markup=get_yes_no_keyboard("order", "заказал(а)")
                )
                await state.set_state(UserFlow.waiting_for_order)
                return
            else:
                try:
                    # Не подписан
                    await callback.message.edit_text(
                        "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                        f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                        reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
                    )
                except:
                    await callback.message.edit_text(
                        f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                        reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
                    )
        except TelegramBadRequest:
            await callback.message.answer(
                "⚠️ Не удалось проверить подписку. Проверьте, что бот — администратор канала."
            )
    else:
        # Не подписан
        try:
            await callback.message.edit_text(
                "❌ Пока вы не подпишетесь на канал — раздача невозможна.\n"
                f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
            )
        except:
            await callback.message.edit_text(
                f"Подпишитесь на {CHANNEL_USERNAME} и нажмите кнопку ниже:",
                reply_markup=get_yes_no_keyboard("subscribe", "подписался(лась)")
            )
        await state.set_state(UserFlow.waiting_for_subcription_to_channel)