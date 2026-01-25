from typing import Any

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Row, Button
from aiogram_dialog.widgets.text import Const, Format
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.interactors.buy_leads.buy_leads import BuyLeads
from axiomai.application.interactors.buy_leads.mark_payment_waiting_confirm import MarkPaymentWaitingConfirm
from axiomai.constants import PRICE_PER_LEAD, KIRILL_CARD_NUMBER, KIRILL_PHONE_NUMBER
from axiomai.infrastructure.telegram.dialogs.states import BuyLeadsStates


async def waiting_for_payment_confirm_getter(dialog_manager: DialogManager, **kwargs: dict[str, Any]) -> dict[str, Any]:
    leads = dialog_manager.dialog_data["leads"]

    return {
        "leads": leads,
        "price_per_lead": PRICE_PER_LEAD,
        "total_amount": leads * PRICE_PER_LEAD,
    }


@inject
async def on_input_lead_amount(
    message: Message, widget: MessageInput, dialog_manager: DialogManager, buy_leads: FromDishka[BuyLeads]
) -> None:
    leads_str = message.text.strip()
    if not leads_str.isdigit():
        await message.answer(text="Введите количество лидов <b>числом</b>, только цифры.")
        return

    leads = int(leads_str)
    if leads <= 0:
        await message.answer("Введите, пожалуйста, положительное число лидов.")
        return

    payment_id = await buy_leads.execute(message.from_user.id, leads)

    dialog_manager.dialog_data["leads"] = leads
    dialog_manager.dialog_data["payment_id"] = payment_id

    await dialog_manager.next()


@inject
async def on_paid_confirmed(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    mark_waiting: FromDishka[MarkPaymentWaitingConfirm],
) -> None:
    payment_id = dialog_manager.dialog_data["payment_id"]

    await mark_waiting.execute(payment_id)
    await callback.message.answer(
        "Спасибо! Мы получили запрос на оплату.\nМенеджер проверит перевод и подтвердит оплату."
    )

    await dialog_manager.done()


async def on_paid_declined(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    await callback.message.answer("Пожалуйста, сделайте перевод на карту и тогда бот заработает.")


buy_leads_dialog = Dialog(
    Window(
        Const(f"Сколько лидов хотите купить?\nСейчас цена 1 лида = {PRICE_PER_LEAD} ₽.\n\nВведите число:"),
        MessageInput(on_input_lead_amount),
        state=BuyLeadsStates.waiting_for_lead_amount,
    ),
    Window(
        Format(
            "Вы хотите купить <b>{leads}</b> лидов по цене <b>{price_per_lead} ₽</b> за лид.\n"
            "Итого к оплате: <b>{total_amount} ₽</b>.\n\n"
            "Реквизиты для оплаты:\n"
            f"• Карта: <code>{KIRILL_CARD_NUMBER}</code> или\n"
            f"• Телефон: <code>{KIRILL_PHONE_NUMBER}</code>\n"
            "• Получатель: <b>Кирилл К. , Т-банк или Сбер</b>\n\n"
        ),
        Row(
            Button(Const("✅ Да, оплатил(а)"), id="paid_yes", on_click=on_paid_confirmed),
            Button(Const("❌ Не оплатил(а)"), id="paid_no", on_click=on_paid_declined),
        ),
        state=BuyLeadsStates.waiting_for_payment_confirm_click,
        getter=waiting_for_payment_confirm_getter,
    ),
)
