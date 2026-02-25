import logging

from aiogram import Bot, Router
from aiogram.types import Message
from aiogram_dialog import ShowMode
from aiogram_dialog.api.protocols import BgManagerFactory
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.models.buyer import Buyer
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import determine_resume_state
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates
from axiomai.tgbot.filters.ignore_self_message import SelfBusinessMessageFilter

logger = logging.getLogger(__name__)

router = Router()
router.business_message.filter(SelfBusinessMessageFilter())


def _pending_step(buyer: Buyer) -> str | None:
    """Возвращает имя первого незавершённого поля или None."""
    if not buyer.is_ordered:
        return "is_ordered"
    if not buyer.is_left_feedback:
        return "is_left_feedback"
    if not buyer.is_cut_labels:
        return "is_cut_labels"
    return None


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


@router.business_message()
@inject
async def on_seller_confirm_screenshot(  # noqa: C901, PLR0912
    message: Message,
    bot: Bot,
    dialog_bg_factory: BgManagerFactory,
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    parts = (message.text or "").strip().split()
    if not parts or parts[0].lower() != "/confirm":
        return

    # Удаляем команду из чата — лид её не увидит
    try:
        await bot.delete_business_messages(
            business_connection_id=message.business_connection_id,
            message_ids=[message.message_id],
        )
    except Exception:  # noqa: BLE001
        logger.warning("could not delete seller confirm command (msg_id=%s)", message.message_id)

    lead_id = message.chat.id

    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(message.business_connection_id)
    if not cabinet:
        logger.warning("confirm: cabinet not found for biz_connection %s", message.business_connection_id)
        return

    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(lead_id, cabinet.id)
    pending_buyers = [b for b in buyers if _pending_step(b) is not None]

    if not pending_buyers:
        logger.info("confirm: no pending buyers for lead %s", lead_id)
        return

    amount: int | None = None

    if len(pending_buyers) == 1:
        target = pending_buyers[0]
        # /confirm {amount}
        if _pending_step(target) == "is_ordered" and len(parts) >= 2:  # noqa: PLR2004
            amount = _parse_int(parts[1])
    else:
        # /confirm {nm_id} или /confirm {nm_id} {amount}
        if len(parts) < 2:  # noqa: PLR2004
            logger.info("confirm: %d pending buyers for lead %s, nm_id required", len(pending_buyers), lead_id)
            return
        nm_id = _parse_int(parts[1])
        if nm_id is None:
            return
        target = next((b for b in pending_buyers if b.nm_id == nm_id), None)
        if not target:
            logger.info("confirm: nm_id %s not found or already complete for lead %s", nm_id, lead_id)
            return
        # /confirm {nm_id} {amount}
        if _pending_step(target) == "is_ordered" and len(parts) >= 3:  # noqa: PLR2004
            amount = _parse_int(parts[2])

    field = _pending_step(target)

    if not target.is_ordered:
        target.is_ordered = True
        if amount is not None:
            target.amount = amount
    if not target.is_left_feedback:
        target.is_left_feedback = True
    if not target.is_cut_labels:
        target.is_cut_labels = True

    await transaction_manager.commit()

    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(lead_id, cabinet.id)
    next_state = determine_resume_state(buyers) or CashbackArticleStates.input_requisites

    bg_manager = dialog_bg_factory.bg(
        bot=bot,
        user_id=lead_id,
        chat_id=lead_id,
        business_connection_id=message.business_connection_id,
    )
    await bg_manager.switch_to(next_state, show_mode=ShowMode.SEND)

    logger.info(
        "seller confirmed step '%s' (amount=%s) for nm_id %s, lead %s -> %s",
        field, amount, target.nm_id, lead_id, next_state,
    )
