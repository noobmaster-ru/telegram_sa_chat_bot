from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import joinedload
from sqlalchemy import select


from src.app.bot.keyboards.reply import kb_menu
from src.infrastructure.db.models import (
    PaymentORM,
    PaymentStatus,
    CashbackTableORM,
    CashbackTableStatus
)
from src.tools.string_converter_class import StringConverter
from src.core.config import constants

from .router import router

@router.callback_query(F.data.startswith("admin_pay_ok:"))
async def admin_confirm_payment(
    callback: CallbackQuery,
    db_session_factory: async_sessionmaker,
):
    """
    Админ подтверждает оплату:
    - payment.status: WAITING_CONFIRM -> SUCCEEDED
    - увеличиваем cabinet.leads_balance на количество лидов из service_data["leads"]
    """
    await callback.answer()
    payment_id = int(callback.data.split(":")[1])
    async with db_session_factory() as session:
        # 1. Грузим платёж вместе с таблицей, кабинетом и пользователем
        result = await session.execute(
            select(PaymentORM)
            .options(
                joinedload(PaymentORM.cashback_table)
                .joinedload(CashbackTableORM.cabinet),
                joinedload(PaymentORM.user),
            )
            .where(PaymentORM.id == payment_id)
        )
        payment: PaymentORM | None = result.scalar_one_or_none()

        if payment is None:
            text = "Платёж не найден"
            await callback.answer(
                text=StringConverter.escape_markdown_v2(text), 
                show_alert=True,
                parse_mode="MarkdownV2"
            )
            return

        if payment.status != PaymentStatus.WAITING_CONFIRM:
            text = "Этот платёж уже обработан"
            await callback.answer(
                text=StringConverter.escape_markdown_v2(text), 
                show_alert=True,
                parse_mode="MarkdownV2"
            )
            return

        cashback_table = payment.cashback_table
        cabinet = cashback_table.cabinet if cashback_table else None
        user = payment.user

        # 2. Берём количество лидов из service_data (по договорённости)
        leads = int(payment.service_data.get("leads", 0) or 0)

        # 3. Обновляем статус платежа
        payment.status = PaymentStatus.SUCCEEDED

        # 4. Обновляем статус таблицы (опционально)
        if cashback_table and cashback_table.status != PaymentStatus.SUCCEEDED:
            cashback_table.status = CashbackTableStatus.PAID

        # 5. Накидываем лиды кабинету
        if cabinet and leads > 0:
            cabinet.leads_balance = (cabinet.leads_balance or 0) + leads

        await session.commit()

    # 6. Обновляем сообщение в админском чате
    text = (
        f"Оплата {payment_id} подтверждена ✅\n"
        f"Лидов начислено: {leads}"
        + (f"\nМагазин: {cabinet.organization_name}" if cabinet else "")
    )
    await callback.message.edit_text(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )

    # 7. Уведомляем селлера
    if user and user.telegram_id:
        text = (
            f"✅ Оплата {payment_id} подтверждена.\n\n"
            f"На ваш кабинет начислено {leads} лидов.\n"
            f"Теперь боту снова можно принимать заявки от клиентов."
        )
        await callback.bot.send_message(
            chat_id=user.telegram_id,
            text=StringConverter.escape_markdown_v2(text),
            reply_markup=kb_menu,
            parse_mode="MarkdownV2"
        )

@router.callback_query(F.data.startswith("admin_pay_fail:"))
async def admin_reject_payment(
    callback: CallbackQuery,
    db_session_factory: async_sessionmaker,
):
    """
    Админ отклоняет оплату:
    - payment.status: WAITING_CONFIRM -> CANCELED
    - cabinet.leads_balance не меняем
    """
    await callback.answer()
    payment_id = int(callback.data.split(":")[1])

    async with db_session_factory() as session:
        result = await session.execute(
            select(PaymentORM)
            .options(
                joinedload(PaymentORM.cashback_table)
                .joinedload(CashbackTableORM.cabinet),
                joinedload(PaymentORM.user),
            )
            .where(PaymentORM.id == payment_id)
        )
        payment: PaymentORM | None = result.scalar_one_or_none()

        if payment is None:
            text = "Платёж не найден"
            await callback.answer(
                text=StringConverter.escape_markdown_v2(text),
                show_alert=True,
                parse_mode="MarkdownV2"
            )
            return

        if payment.status != PaymentStatus.WAITING_CONFIRM:
            text = "Этот платёж уже обработан"
            await callback.answer(
                text=StringConverter.escape_markdown_v2(text), 
                show_alert=True,
                parse_mode="MarkdownV2"
            )
            return

        cashback_table = payment.cashback_table
        cabinet = cashback_table.cabinet if cashback_table else None
        user = payment.user

        # Статус → CANCELED
        payment.status = PaymentStatus.CANCELED
        # при желании можно прописать причину:
        # payment.canceled_reason = "Отклонено администратором"

        await session.commit()
    text = (
        f"Оплата {payment_id} отклонена ❌"
        + (f"\nМагазин: {cabinet.organization_name}" if cabinet else "")
    )
    await callback.message.edit_text(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )

    if user and user.telegram_id:
        text = (
            f"❌ Оплата {payment_id} отклонена.\n\n"
            f"Если вы уже отправляли перевод, свяжитесь, пожалуйста, с поддержкой: {constants.ADMIN_USERNAME}"
        )
        await callback.bot.send_message(
            chat_id=user.telegram_id,
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )