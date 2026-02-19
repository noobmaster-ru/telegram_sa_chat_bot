from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.interactors.refill_balance.mark_payment_waiting_confirm import (
    MarkRefillBalancePaymentWaitingConfirm,
)
from axiomai.application.interactors.refill_balance.refill_balance import RefillBalance
from axiomai.infrastructure.telegram.dialogs.states import RefillBalanceStates


async def waiting_for_payment_confirm_getter(dialog_manager: DialogManager, **kwargs: dict[str, Any]) -> dict[str, Any]:
    amount = dialog_manager.dialog_data["amount"]

    return {"amount": amount}


@inject
async def on_input_amount(
    message: Message, widget: MessageInput, dialog_manager: DialogManager, refill_balance: FromDishka[RefillBalance]
) -> None:
    amount_str = message.text.strip()
    if not amount_str.isdigit():
        await message.answer("Введите сумму <b>числом</b>, только цифры.")
        return

    amount = int(amount_str)
    if amount <= 0:
        await message.answer("Введите, пожалуйста, положительное число.")
        return

    payment_id = await refill_balance.execute(message.from_user.id, amount)

    dialog_manager.dialog_data["amount"] = amount
    dialog_manager.dialog_data["payment_id"] = payment_id

    await dialog_manager.next()


@inject
async def on_paid_confirmed(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mark_waiting: FromDishka[MarkRefillBalancePaymentWaitingConfirm],
) -> None:
    payment_id = dialog_manager.dialog_data["payment_id"]

    await mark_waiting.execute(payment_id)
    await callback.message.answer(
        "Спасибо! Мы получили запрос на оплату.\nМенеджер проверит перевод и подтвердит оплату."
    )

    await dialog_manager.done(show_mode=ShowMode.SEND)


refill_balance_dialog = Dialog(
    Window(
        Const("Введите сумму для пополнения баланса:"),
        MessageInput(on_input_amount),
        state=RefillBalanceStates.waiting_for_amount,
    ),
    Window(
        Format(
            "Итого к оплате: <b>{amount} ₽</b>.\n\n"
            "РЕКВИЗИТЫ:\n"
            "• БИК: <code>044525974</code> или\n"
            "• Кор. счёт: <code>30101810145250000974</code>\n"
            "• Расчётный счёт: <code>40802810800004912384</code>\n\n"
            "В качестве получателя укажите:\n"
            "<code>Индивидуальный предприниматель Козлов Артем Андреевич</code> и ИНН = <code>760401197136</code>"
        ),
        Row(
            Button(Const("✅ Да, оплатил(а)"), id="paid_yes", on_click=on_paid_confirmed),
        ),
        state=RefillBalanceStates.waiting_for_payment_confirm_click,
        getter=waiting_for_payment_confirm_getter,
    ),
)
