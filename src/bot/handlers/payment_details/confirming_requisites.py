from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.methods import ReadBusinessMessage


from src.services.google_sheets_class import GoogleSheetClass
from src.bot.states.user_flow import UserFlow
from src.bot.utils.last_activity import update_last_activity

from .router import router

@router.callback_query(StateFilter(UserFlow.confirming_requisites), F.data == "confirm_requisites_no")
async def confirm_requisites_no(
    callback: CallbackQuery, 
    state: FSMContext
):
    """
    Пользователь указал, что реквизиты неверные — начинаем ввод заново.
    """
    await callback.message.bot(
        ReadBusinessMessage(
            business_connection_id=callback.message.business_connection_id,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    )
    await callback.answer()
    
    # Получаем текущее состояние FSM
    user_data = await state.get_data()
    
    # Удаленияем определенного ключа (например, 'username') из словаря Python
    if 'bank' in user_data:
        del user_data['bank']
    if 'amount' in user_data:
        del user_data['amount']
    if 'phone_number' in user_data:
        del user_data['phone_number']
    if 'card_number' in user_data:
        del user_data['card_number']
        
    # Обновление данных в FSMContext
    await state.set_data(user_data)
    
    # ставим новое состояние
    msg = await callback.message.edit_text(
        "❌ Хорошо, давайте попробуем ещё раз.\n"
        "Отправьте номер телефона, сумму для оплаты , название банка и (если есть) номер карты одним сообщением."
    )
    await state.set_state(UserFlow.waiting_for_requisites)
    await update_last_activity(state, msg)

@router.callback_query(StateFilter(UserFlow.confirming_requisites), F.data == "confirm_requisites_yes")
async def confirm_requisites_yes(
    callback: CallbackQuery, 
    state: FSMContext,
    spreadsheet: GoogleSheetClass,
):
    await callback.answer()
    """
    Пользователь указал, что реквизиты верные — сохраняем их в гугл таблицу и очищаем состояние.
    """
    await callback.message.bot(
        ReadBusinessMessage(
            business_connection_id=callback.message.business_connection_id,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )
    )
    data = await state.get_data()
    telegram_id = callback.from_user.id


    # записываем данные в гугл-таблицу и однвременно обновим последнее время записи
    await spreadsheet.write_requisites_into_google_sheets_and_update_last_time_message(
        telegram_id=telegram_id,
        card_number=data.get('card_number', '-'),
        phone_number=data.get('phone_number','-'),
        bank=data.get('bank','-'),
        amount=data.get('amount','-'),
    )

    await state.set_state(UserFlow.continue_dialog)
    msg = await callback.message.edit_text(
        f"📩 Реквизиты записаны:\n"
        f"Номер карты: `{data.get('card_number', '-')}`\n"
        f"Номер телефона: `{data.get('phone_number', '-')}`\n"
        f"Банк: {data.get('bank', '-')}\n"
        f"Сумма: `{data.get('amount', '-')}`\n\n"
        f"Ожидайте выплату в ближайшее время, спасибо ☺️",
        parse_mode="Markdown"
    )
    await update_last_activity(state, msg)
    # удаляем данные из состояния и из redis (но можно и оставить так-то)
    # await state.set_data({})