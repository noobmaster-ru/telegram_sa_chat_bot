from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from google_sheets.google_sheets_class import GoogleSheetClass

from handlers.keyboards import (
    get_different_number_of_buttons_keyboard,
    get_subscription_check_keyboard,
    get_agreement_keyboard
)

router = Router()

CHANNEL_USERNAME = "@viktoriya_cash"  # username канала

async def process_button_click(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    button_name: str,
    value: str,
):
    username = callback.from_user.username or "без username"

    # обновляем статус в таблице
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username, 
        button_name=button_name, 
        value=value
    )
    # генерируем новые кнопки только для оставшихся
    remaining_buttons = spreadsheet.get_remaining_buttons(
        sheet_name=BUYERS_SHEET_NAME, username=username
    )

    if remaining_buttons:
        await callback.message.answer(
            f"✅ Ваш ответ '{value}' зафиксирован.",
            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons),
        )
    else:
        await callback.message.answer("✅ Все статусы заполнены, спасибо!")
    await callback.answer()


# @router.callback_query(F.data.startswith("agree_"))
# async def handle_feedback(
#     callback: CallbackQuery, 
#     spreadsheet: GoogleSheetClass, 
#     BUYERS_SHEET_NAME: str
# ):
#     value = "Да" if callback.data == "agree_yes" else "Нет"
#     await process_button_click(callback, spreadsheet, BUYERS_SHEET_NAME, "agree", value)

@router.callback_query(F.data.startswith("agree_"))
async def handle_agreement(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "agree_yes" else "Нет"

    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME,
        username=username,
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
                    username=username, 
                    button_name="subscribe", 
                    value="Да"
                )
                remaining_buttons = spreadsheet.get_remaining_buttons(
                    sheet_name=BUYERS_SHEET_NAME,
                    username=username
                )
                if remaining_buttons:
                    await callback.message.answer(
                        "Продолжаем:",
                        reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
                    )
                else:
                    await callback.message.answer("✅ Все статусы заполнены, спасибо!")
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
            "❌ Без согласия участие невозможно.",
            get_agreement_keyboard
        )

    await callback.answer()

@router.callback_query(F.data.startswith("subscribed_"))
async def handle_subscribed_check(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"

    try:
        member = await callback.message.bot.get_chat_member(
            chat_id=CHANNEL_USERNAME,
            user_id=callback.from_user.id
        )
        if member.status in ("member", "administrator", "creator"):
            await callback.message.answer("✅ Подписка подтверждена! Продолжаем.")
            remaining_buttons = spreadsheet.get_remaining_buttons(
                sheet_name=BUYERS_SHEET_NAME,
                username=username
            )
            if remaining_buttons:
                await callback.message.answer(
                    "Продолжаем:",
                    reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
                )
            else:
                await callback.message.answer("✅ Все статусы заполнены, спасибо!")
        else:
            await callback.message.answer(
                "❌ Вы всё ещё не подписаны. Подпишитесь на канал и попробуйте снова.",
                reply_markup=get_subscription_check_keyboard()
            )
    except TelegramBadRequest:
        await callback.message.answer(
            "⚠️ Не удалось проверить подписку. Проверьте, что бот — администратор канала."
        )

    await callback.answer()


@router.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str
):
    value = "Да" if callback.data == "feedback_yes" else "Нет"
    await process_button_click(callback, spreadsheet, BUYERS_SHEET_NAME, "feedback", value)





@router.callback_query(F.data.startswith("order_"))
async def handle_order(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str
):
    value = "Да" if callback.data == "order_yes" else "Нет"
    await process_button_click(callback, spreadsheet, BUYERS_SHEET_NAME, "order", value)






@router.callback_query(F.data.startswith("shk_"))
async def handle_shk(
    callback: CallbackQuery, 
    spreadsheet: GoogleSheetClass, 
    BUYERS_SHEET_NAME: str
):
    value = "Да" if callback.data == "shk_yes" else "Нет"
    await process_button_click(callback, spreadsheet, BUYERS_SHEET_NAME, "shk", value)