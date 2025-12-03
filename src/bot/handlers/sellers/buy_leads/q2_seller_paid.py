from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from src.bot.states.seller import SellerStates
from src.db.models import (
    PaymentORM,
    PaymentStatus,
    CashbackTableORM,
)
from src.bot.keyboards.inline.build_payment_admin_keyboard import (
    build_payment_admin_keyboard,
)
from src.core.config import constants

from .router import router


@router.callback_query(
    F.data.startswith("payment_yes"), 
    StateFilter(SellerStates.waiting_for_payment_confirm_click),
)
async def seller_clicked_paid(
    callback: CallbackQuery,
    state: FSMContext,
    db_session_factory: async_sessionmaker,
):
    await callback.answer()

    data = await state.get_data()
    payment_id = data.get("payment_id")
    leads = data.get("leads_to_buy")
    amount = data.get("total_amount")

    if payment_id is None:
        await callback.message.answer(
            "Не удалось найти данные по оплате. Попробуйте, пожалуйста, начать заново."
        )
        return

    async with db_session_factory() as session:
        # 1. Переводим payment в WAITING_CONFIRM
        payment = await session.get(PaymentORM, payment_id)
        if payment is None:
            await callback.message.answer(
                "Платёж не найден. Попробуйте, пожалуйста, начать заново."
            )
            return

        payment.status = PaymentStatus.WAITING_CONFIRM
        await session.commit()
        await session.refresh(payment)

        # 2. Пытаемся определить название кабинета через cashback_table -> cabinet
        cabinet_name = "Неизвестный кабинет"
        if payment.cashback_table_id is not None:
            result = await session.execute(
                select(CashbackTableORM)
                .options(selectinload(CashbackTableORM.cabinet))
                .where(CashbackTableORM.id == payment.cashback_table_id)
            )
            cashback_table = result.scalar_one_or_none()
            if cashback_table and cashback_table.cabinet:
                cabinet_name = cashback_table.cabinet.organization_name

    # чистим клавиатуру под сообщением селлера
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "Спасибо! Мы получили запрос на оплату.\n"
        "Менеджер проверит перевод и подтвердит оплату."
    )

    # 3. Уведомляем админский чат
    admin_chat_id = constants.ADMIN_ID_LIST[0]  # 694144143 — ты
    text = (
        f"💸 Новая оплата #{payment_id}\n"
        f"Кабинет: {cabinet_name}\n"
        f"Лидов: {leads}\n"
        f"Сумма: {amount} ₽\n\n"
        f"Подтвердите, пожалуйста."
    )

    await callback.bot.send_message(
        chat_id=admin_chat_id,
        text=text,
        reply_markup=build_payment_admin_keyboard(payment_id),
    )
    await state.set_state(SellerStates.waiting_for_tap_to_menu)
    
@router.message(StateFilter(SellerStates.waiting_for_payment_confirm_click)) 
async def seller_texted(message: Message):
    await message.answer("Пожалуйста, нажмите на кнопку выше")
    
    
@router.callback_query(F.data.startswith("payment_no"),StateFilter(SellerStates.waiting_for_payment_confirm_click))
async def seller_texted(callback: CallbackQuery):
    await callback.message.answer("Пожалуйста, сделайте перевод на карту и тогда бот заработает")