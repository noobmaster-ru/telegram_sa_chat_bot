from aiogram import F, Router
from aiogram.types import CallbackQuery
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.payment import PaymentAlreadyProcessedError, PaymentNotFoundError
from axiomai.application.interactors.buy_leads.cancel_payment import CancelPayment
from axiomai.application.interactors.buy_leads.confirm_payment import ConfirmPayment

router = Router()


@router.callback_query(F.data.startswith("admin_pay_ok:"))
@inject
async def admin_confirm_payment(callback: CallbackQuery, confirm_payment: FromDishka[ConfirmPayment]) -> None:
    """
    Админ подтверждает оплату:
    - payment.status: WAITING_CONFIRM -> SUCCEEDED
    - увеличиваем cabinet.leads_balance на количество лидов из service_data["leads"]
    """
    await callback.answer()
    payment_id = int(callback.data.split(":")[1])

    try:
        await confirm_payment.execute(callback.from_user.id, payment_id)
    except PaymentNotFoundError:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    except PaymentAlreadyProcessedError:
        await callback.answer("❌ Платеж уже был обработан", show_alert=True)
        return

    await callback.message.edit_text(callback.message.text + "\n\n✅ Оплата подтверждена.")


@router.callback_query(F.data.startswith("admin_pay_fail:"))
@inject
async def admin_reject_payment(callback: CallbackQuery, cancel_payment: FromDishka[CancelPayment]) -> None:
    """
    Админ отклоняет оплату:
    - payment.status: WAITING_CONFIRM -> CANCELED
    - cabinet.leads_balance не меняем
    """
    await callback.answer()
    payment_id = int(callback.data.split(":")[1])

    try:
        await cancel_payment.execute(callback.from_user.id, payment_id)
    except PaymentNotFoundError:
        await callback.answer("❌ Платеж не найден", show_alert=True)
        return
    except PaymentAlreadyProcessedError:
        await callback.answer("❌ Платеж уже был обработан", show_alert=True)
        return

    await callback.message.edit_text(callback.message.text + "\n\n❌ Оплата отклонена.")
