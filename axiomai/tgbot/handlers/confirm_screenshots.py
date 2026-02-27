import logging

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram_dialog import ShowMode, StartMode
from aiogram_dialog.api.exceptions import NoContextError
from aiogram_dialog.api.protocols import BgManagerFactory
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.buyer import BuyerAlreadyOrderedError
from axiomai.application.interactors.cancel_buyer import CancelBuyer
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import determine_resume_state
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates
from axiomai.tgbot.filters.ignore_self_message import SelfBusinessMessageFilter

logger = logging.getLogger(__name__)

router = Router()
router.business_message.filter(SelfBusinessMessageFilter())


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


@router.business_message(Command("confirm"))
@inject
async def on_seller_confirm_screenshot(
    message: Message,
    command: CommandObject,
    bot: Bot,
    dialog_bg_factory: BgManagerFactory,
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
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

    args = command.args.split()

    amount = None

    if len(args) == 1:
        nm_id = _parse_int(args[0])
    else:
        nm_id, amount = _parse_int(args[0]), _parse_int(args[1])

    target = next((b for b in buyers if b.nm_id == nm_id), None)

    if not target:
        target = buyers[0]

    if not target.is_ordered:
        target.is_ordered = True
        if amount is not None:
            target.amount = amount
    elif not target.is_left_feedback:
        target.is_left_feedback = True
    elif not target.is_cut_labels:
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
    try:
        await bg_manager.switch_to(next_state, show_mode=ShowMode.SEND)
    except NoContextError:
        await bg_manager.start(next_state, show_mode=ShowMode.SEND, mode=StartMode.RESET_STACK)

    logger.info(
        "seller confirmed step (amount=%s) for nm_id %s, lead %s -> %s", amount, target.nm_id, lead_id, next_state,
    )


@router.business_message(Command("cancel"))
@inject
async def on_seller_cancel_buyer(
    message: Message,
    command: CommandObject,
    bot: Bot,
    dialog_bg_factory: BgManagerFactory,
    cabinet_gateway: FromDishka[CabinetGateway],
    buyer_gateway: FromDishka[BuyerGateway],
    cancel_buyer: FromDishka[CancelBuyer],
) -> None:
    try:
        await bot.delete_business_messages(
            business_connection_id=message.business_connection_id,
            message_ids=[message.message_id],
        )
    except Exception:  # noqa: BLE001
        logger.warning("could not delete seller cancel command (msg_id=%s)", message.message_id)

    args = (command.args or "").split()
    lead_id = message.chat.id

    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(message.business_connection_id)
    if not cabinet:
        logger.warning("cancel: cabinet not found for biz_connection %s", message.business_connection_id)
        return

    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(lead_id, cabinet.id)
    cancellable = [b for b in buyers if not b.is_ordered]

    if args:
        nm_id = _parse_int(args[0])
        if nm_id is None:
            return
        target = next((b for b in cancellable if b.nm_id == nm_id), None)
    elif len(cancellable) == 1:
        target = cancellable[0]
    else:
        logger.info("cancel: %d cancellable buyers for lead %s, nm_id required", len(cancellable), lead_id)
        return

    if not target:
        logger.info("cancel: nm_id not found or already ordered for lead %s", lead_id)
        return

    try:
        await cancel_buyer.execute(target.id)
    except BuyerAlreadyOrderedError:
        logger.info("cancel: buyer %s already ordered, cannot cancel", target.id)
        return

    remaining = await buyer_gateway.get_incompleted_buyers_by_telegram_id_and_cabinet_id(lead_id, cabinet.id)

    bg_manager = dialog_bg_factory.bg(
        bot=bot,
        user_id=lead_id,
        chat_id=lead_id,
        business_connection_id=message.business_connection_id,
    )
    resume_state = determine_resume_state(remaining) if remaining else None
    if resume_state:
        try:
            await bg_manager.switch_to(resume_state, show_mode=ShowMode.SEND)
        except NoContextError:
            await bg_manager.start(resume_state, show_mode=ShowMode.SEND, mode=StartMode.RESET_STACK)
    else:
        await bg_manager.done()

    logger.info("seller cancelled nm_id %s for lead %s", target.nm_id, lead_id)
