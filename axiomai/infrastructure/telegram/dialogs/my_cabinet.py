from typing import Any

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.text import Format
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.telegram.dialogs.states import MyCabinetStates


@inject
async def my_cabinet_getter(
    dialog_manager: DialogManager, cabinet_gateway: FromDishka[CabinetGateway], **kwargs: dict[str, Any]
) -> dict[str, Any]:
    cabinet = await cabinet_gateway.get_cabinet_by_telegram_id_or_business_account_id(dialog_manager.event.from_user.id)
    if not cabinet:
        raise CabinetNotFoundError

    return {
        "cabinet": cabinet,
        "user": (
            f"@{dialog_manager.event.from_user.username}"
            if dialog_manager.event.from_user.username
            else dialog_manager.event.from_user.first_name
        ),
    }


my_cabinet_dialog = Dialog(
    Window(
        Format(
            "⚡️ Axiom AI · Личный кабинет\n\n"
            "👤 Пользователь: {user}\n"
            "🔥 Бизнес акканут: <code>{cabinet.business_account_id}</code>\n\n"
            "💎 Баланс лидов: <code>{cabinet.leads_balance}</code> лидов"
        ),
        state=MyCabinetStates.select_option,
        getter=my_cabinet_getter,
    ),
)
