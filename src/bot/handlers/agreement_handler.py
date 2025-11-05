from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext


from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow


from src.services.google_sheets_class import GoogleSheetClass

router = Router()

@router.callback_query(F.data.startswith("agree_"))
async def handle_agreement(
    callback: CallbackQuery,
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    CHANNEL_USERNAME: str,
):
    await callback.answer()
    telegram_id = callback.from_user.id
    value = "Да" if callback.data == "agree_yes" else "Нет"
    data = await state.get_data()
    nm_id = data.get("nm_id")
    

    await spreadsheet.update_buyer_button_and_time(
        telegram_id=telegram_id,
        button_name="agree",
        value=value,
        is_tap_to_keyboard=True
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
                await callback.message.edit_text(
                    "✅ Отлично! Вы подписаны на канал.",
                )


                await spreadsheet.update_buyer_button_and_time(
                    telegram_id=telegram_id,
                    button_name="subscribe",
                    value="Да",
                    is_tap_to_keyboard=True
                )
                # 👉 start quiz_handlers
                await state.set_state(UserFlow.waiting_for_order)
                await callback.message.edit_text(
                    f"📦 Вы заказали товар {nm_id}?", 
                    reply_markup=get_yes_no_keyboard("order", "заказал(а)")
                )
                return
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
        except TelegramBadRequest:
            await callback.message.answer(
                "⚠️ Не удалось проверить подписку. Проверьте, что бот — администратор канала."
            )
    else:
        try:
            await callback.message.edit_text(
                "Без согласия участие невозможно. Вы согласны на условия?",
                reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
            )
        except:
            await callback.message.edit_text(
                "Вы согласны на условия?",
                reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
            )
        await state.set_state(UserFlow.waiting_for_agreement)
        return 