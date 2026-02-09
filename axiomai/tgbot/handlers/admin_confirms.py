from aiogram import F, Router
from aiogram.types import CallbackQuery
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.payment import PaymentAlreadyProcessedError, PaymentNotFoundError
from axiomai.application.interactors.buy_leads.cancel_payment import CancelBuyLeadsPayment
from axiomai.application.interactors.buy_leads.confirm_payment import ConfirmBuyLeadsPayment
from axiomai.application.interactors.refill_balance.cancel_payment import CancelRefillBalancePayment
from axiomai.application.interactors.refill_balance.confirm_payment import ConfirmRefillBalancePayment
from axiomai.infrastructure.database.gateways.payment import PaymentGateway

router = Router()


@router.callback_query(F.data.startswith("admin_pay_ok:"))
@inject
async def admin_confirm_payment(
    callback: CallbackQuery,
    payment_gateway: FromDishka[PaymentGateway],
    confirm_buy_leads: FromDishka[ConfirmBuyLeadsPayment],
    confirm_refill_balance: FromDishka[ConfirmRefillBalancePayment],
) -> None:
    """
    Админ подтверждает оплату:
    - payment.status: WAITING_CONFIRM -> SUCCEEDED
    """
    await callback.answer()
    payment_id = int(callback.data.split(":")[1])

    payment = await payment_gateway.get_payment_by_id(payment_id)
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        await callback.message.edit_text(callback.message.text + "\n\n❌ Платеж не найден")
        return

    try:
        if payment.service_data.get("type") == "buy_leads":
            await confirm_buy_leads.execute(callback.from_user.id, payment_id)
        else:
            await confirm_refill_balance.execute(callback.from_user.id, payment_id)
    except PaymentNotFoundError:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    except PaymentAlreadyProcessedError:
        await callback.answer("❌ Платеж уже был обработан", show_alert=True)
        return

    await callback.message.edit_text(callback.message.text + "\n\n✅ Оплата подтверждена.")


@router.callback_query(F.data.startswith("admin_pay_fail:"))
@inject
async def admin_reject_payment(
    callback: CallbackQuery,
    payment_gateway: FromDishka[PaymentGateway],
    cancel_buy_leads: FromDishka[CancelBuyLeadsPayment],
    cancel_refill_balance: FromDishka[CancelRefillBalancePayment],
) -> None:
    """
    Админ отклоняет оплату:
    - payment.status: WAITING_CONFIRM -> CANCELED
    - cabinet.leads_balance не меняем
    """
    await callback.answer()
    payment_id = int(callback.data.split(":")[1])

    payment = await payment_gateway.get_payment_by_id(payment_id)
    if not payment:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        await callback.message.edit_text(callback.message.text + "\n\n❌ Платеж не найден")
        return

    try:
        if payment.service_data.get("type") == "buy_leads":
            await cancel_buy_leads.execute(callback.from_user.id, payment_id)
        else:
            await cancel_refill_balance.execute(callback.from_user.id, payment_id)
    except PaymentNotFoundError:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    except PaymentAlreadyProcessedError:
        await callback.answer("❌ Платеж уже был обработан", show_alert=True)
        return

    await callback.message.edit_text(callback.message.text + "\n\n❌ Оплата отклонена.")
