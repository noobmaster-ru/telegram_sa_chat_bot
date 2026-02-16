import asyncio
import logging
from typing import Any
from urllib import error

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, URLInputFile
from aiogram_dialog import DialogManager, ShowMode
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.exceptions.superbanking import CreatePaymentError, SignPaymentError, SkipSuperbankingError
from axiomai.application.interactors.create_superbanking_payment import CreateSuperbankingPayment
from axiomai.constants import (
    BANK_PATTERN,
    CARD_CLEAN_RE,
    CARD_PATTERN,
    PHONE_PATTERN,
    TIME_SLEEP_BEFORE_CONFIRM_PAYMENT,
    WB_CHANNEL_NAME,
)
from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.superbanking import Superbanking

logger = logging.getLogger(__name__)


@inject
async def on_input_requisites(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    superbanking: FromDishka[Superbanking],
    buyer_gateway: FromDishka[BuyerGateway],
    cabinet_gateway: FromDishka[CabinetGateway],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(message.business_connection_id)
    if not cabinet:
        raise ValueError(f"Cabinet with business connection id {message.business_connection_id} not found")

    buyers = await buyer_gateway.get_active_buyers_by_telegram_id_and_cabinet_id(message.from_user.id, cabinet.id)
    completed_buyers = [b for b in buyers if b.is_cut_labels]

    if not completed_buyers:
        await message.answer("К сожалению что-то пошло не так, попробуйте пройти процесс заново.")
        await dialog_manager.done()
        return

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    requisites = message.text.strip()

    if card_match := CARD_PATTERN.search(requisites):
        dialog_manager.dialog_data["card_number"] = CARD_CLEAN_RE.sub("", card_match.group())
    if phone_match := PHONE_PATTERN.search(requisites):
        dialog_manager.dialog_data["phone_number"] = phone_match.group()
    if bank_match := BANK_PATTERN.search(requisites):
        bank_alias = bank_match.group()
        bank_name_rus = superbanking.get_bank_name_rus(bank_alias)
        dialog_manager.dialog_data["bank"] = bank_name_rus or bank_alias.capitalize()
    elif bank_name_rus := superbanking.get_bank_name_rus(requisites):
        dialog_manager.dialog_data["bank"] = bank_name_rus

    await dialog_manager.show(ShowMode.SEND)


@inject
async def on_confirm_requisites(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    superbanking: FromDishka[Superbanking],
    create_superbanking_payment: FromDishka[CreateSuperbankingPayment],
    cabinet_gateway: FromDishka[CabinetGateway],
) -> None:
    logger.info("on_confirm_requisites started: telegram_id=%s", callback.from_user.id)

    await callback.message.edit_text(f"{callback.message.text[:-1]}: <b>Да</b>")
    await callback.message.answer("Ожидайте выплату в ближайшее время, спасибо ☺")

    logger.info(
        "on_confirm_requisites resolving cabinet: telegram_id=%s, business_connection_id=%s",
        callback.from_user.id,
        callback.message.business_connection_id,
    )

    cabinet = await cabinet_gateway.get_cabinet_by_business_connection_id(callback.message.business_connection_id)
    if not cabinet:
        raise ValueError(f"Cabinet with business connection id {callback.message.business_connection_id} not found")

    order_number, payout_error_message = _create_superbanking_payout(
        telegram_id=callback.from_user.id,
        cabinet_id=cabinet.id,
        dialog_manager=dialog_manager,
        create_superbanking_payment=create_superbanking_payment,
    )

    if order_number is None:
        if payout_error_message:
            await callback.message.answer(payout_error_message)
        await callback.message.answer(f"Подписывайтесь на наш канал {WB_CHANNEL_NAME} , там будет много интересных товаров")
        await dialog_manager.done()
        return

    logger.info(
        "on_confirm_requisites scheduling receipt check: telegram_id=%s, order_number=%s",
        callback.from_user.id,
        order_number,
    )
    task = asyncio.create_task(
        _send_receipt_after_confirm(
            superbanking=superbanking,
            message=callback.message,
            order_number=order_number,
        )
    )
    task.add_done_callback(lambda _: None)
    # тут можно вставить отправку ссылки на канал, но я вставил её в _send_receipt_after_confirm, чтобы отправилось после чека
    await dialog_manager.done()


async def _create_superbanking_payout(
    *,
    telegram_id: int,
    cabinet_id: int,
    dialog_manager: DialogManager,
    create_superbanking_payment: CreateSuperbankingPayment,
) -> tuple[str | None, str]:
    logger.info("on_confirm_requisites creating Superbanking payment: telegram_id=%s", telegram_id)

    order_number = None
    payout_error_message = None
    try:
        order_number = await create_superbanking_payment.execute(
            telegram_id=telegram_id,
            cabinet_id=cabinet_id,
            phone_number=dialog_manager.dialog_data.get("phone_number"),
            bank=dialog_manager.dialog_data.get("bank"),
        )

    except CreatePaymentError:
        logger.warning("on_confirm_requisites create_payment failed: telegram_id=%s", telegram_id)
        payout_error_message = "Не удалось инициировать выплату. Мы свяжемся с вами."
    except SignPaymentError:
        logger.warning("on_confirm_requisites sign_payment failed: telegram_id=%s", telegram_id)
        payout_error_message = "Не удалось отправить выплату. Мы свяжемся с вами."
    except Exception:
        payout_error_message = "Не удалось инициировать выплату. Мы свяжемся с вами."
        logger.exception("Failed to create Superbanking payout for telegram_id=%s", telegram_id)
    except SkipSuperbankingError as exc:
        logger.info(
            "on_confirm_requisites skipping Superbanking: cabinet_id=%s, is_superbanking_connect=%s",
            exc.cabinet_id,
            exc.is_superbanking_connect,
        )

    if payout_error_message:
        return None, payout_error_message

    logger.info(
        "on_confirm_requisites Superbanking payment created: buyer_id=%s, order_number=%s",
        telegram_id,
        order_number,
    )
    return order_number, ""


async def _send_receipt_after_confirm(
    *,
    superbanking: Superbanking,
    message: Message,
    order_number: str,
) -> None:
    await asyncio.sleep(TIME_SLEEP_BEFORE_CONFIRM_PAYMENT)

    try:
        check_url = superbanking.confirm_operation(order_number=order_number)
    except (ValueError, error.HTTPError, error.URLError):
        logger.exception(
            "Failed to confirm_operation() Superbanking payout for telegram_id=%s", message.from_user.id
        )
        await message.answer("Чек будет доступен чуть позже. Мы пришлём его дополнительно.")
        return

    pdf_file = URLInputFile(
        check_url,
        filename="Чек.pdf",
    )
    await message.answer_document(
        document=pdf_file,
        caption="Чек по выплате",
    )

    # отправляем ссылку на канал после чека в самом конце сценария
    await message.answer(f"Подписывайтесь на наш канал {WB_CHANNEL_NAME} , там будет много интересных товаров")


async def on_decline_requisites(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager) -> None:
    if "bank" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["bank"]
    if "phone_number" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["phone_number"]
    if "card_number" in dialog_manager.dialog_data:
        del dialog_manager.dialog_data["card_number"]

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "❌ Хорошо, давайте попробуем ещё раз (по порядку запишем всё заново)\n"
        "Отправьте номер телефона в формате:\n\n<code>+7910XXXXXXX</code>"
    )

    dialog_manager.show_mode = ShowMode.NO_UPDATE
