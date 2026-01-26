from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.constants import AMOUNT_PATTERN, BANK_PATTERN, CARD_CLEAN_RE, CARD_PATTERN, PHONE_PATTERN
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.superbanking import Superbanking
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates


@inject
async def article_getter(
    dialog_manager: DialogManager, casback_table_gateway: FromDishka[CashbackTableGateway], **kwargs: dict[str, Any]
) -> dict[str, Any]:
    article = await casback_table_gateway.get_cashback_article_by_id(dialog_manager.start_data["article_id"])

    return {"article": article}


async def requisites_getter(dialog_manager: DialogManager, **kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "amount": dialog_manager.dialog_data.get("amount"),
        "card_number": dialog_manager.dialog_data.get("card_number"),
        "phone_number": dialog_manager.dialog_data.get("phone_number"),
        "bank": dialog_manager.dialog_data.get("bank"),
    }


@inject
async def on_input_order_screenshot(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
    cashback_table_gateway: FromDishka[CashbackTableGateway],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото скриншота заказа")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    article = await cashback_table_gateway.get_cashback_article_by_id(dialog_manager.start_data["article_id"])

    await message.answer("⏳ Проверяю скриншот заказа...")

    result = await openai_gateway.classify_order_screenshot(
        photo_url, article.title, article.brand_name, article.image_url
    )

    if not result["is_order"]:
        cancel_reason = result["cancel_reason"]
        if cancel_reason is None:
            cancel_reason = "Попробуйте отправить фото сюда еще раз"
        await message.answer(f"❌ Заказ не найден на скриншоте\n\n<code>{cancel_reason}</code>")
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    dialog_manager.dialog_data["gpt_amount"] = result["price"]
    await message.answer("✅ Скриншот заказа принят!")
    await dialog_manager.next(ShowMode.SEND)


@inject
async def on_input_feedback_screenshot(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
    cashback_table_gateway: FromDishka[CashbackTableGateway],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото скриншота отзыва")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    article = await cashback_table_gateway.get_cashback_article_by_id(dialog_manager.start_data["article_id"])

    await message.answer("⏳ Проверяю скриншот отзыва...")

    result = await openai_gateway.classify_feedback_screenshot(photo_url, article.title, article.brand_name)

    if not result["is_feedback"]:
        cancel_reason = result["cancel_reason"]
        if cancel_reason is None:
            cancel_reason = "Попробуйте отправить фото сюда еще раз"
        await message.answer(f"❌ Отзыв не найден на скриншоте\n\n<code>{cancel_reason}</code>")
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await message.answer("✅ Скриншот отзыва принят!")
    await dialog_manager.next(ShowMode.SEND)


@inject
async def on_input_cut_labels_photo(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото разрезанных этикеток")
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    await message.answer("⏳ Проверяю фотографию разрезанных этикеток...")

    result = await openai_gateway.classify_cut_labels_photo(photo_url)

    if not result["is_cut_labels"]:
        cancel_reason = result["cancel_reason"]
        if cancel_reason is None:
            cancel_reason = "Попробуйте разрезать этикетки еще раз и отправите фото сюда"
        await message.answer(f"❌ Фото разрезанных штрихкодов не принято\n\n<code>{cancel_reason}</code>")
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await message.answer("✅ Фотография разрезанных этикеток принята!")
    await message.answer("☺ Вы прислали все фотографии, которые были нам нужны. Спасибо!")

    await dialog_manager.next(ShowMode.SEND)


@inject
async def on_input_requisites(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    superbanking: FromDishka[Superbanking],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    requisites = message.text.strip()

    if dialog_manager.dialog_data["gpt_amount"]:
        dialog_manager.dialog_data["amount"] = dialog_manager.dialog_data["gpt_amount"]

    if card_match := CARD_PATTERN.search(requisites):
        dialog_manager.dialog_data["card_number"] = CARD_CLEAN_RE.sub("", card_match.group())
    if (amount_match := AMOUNT_PATTERN.search(requisites)) and (not dialog_manager.dialog_data["gpt_amount"]):
        dialog_manager.dialog_data["amount"] = amount_match.group(1)
    if phone_match := PHONE_PATTERN.search(requisites):
        dialog_manager.dialog_data["phone_number"] = phone_match.group()
    if bank_match := BANK_PATTERN.search(requisites):
        bank_alias = bank_match.group()
        bank_name_rus = superbanking.get_bank_name_rus(bank_alias)
        dialog_manager.dialog_data["bank"] = bank_name_rus or bank_alias.capitalize()
    elif bank_name_rus := superbanking.get_bank_name_rus(requisites):
        dialog_manager.dialog_data["bank"] = bank_name_rus

    await dialog_manager.show(ShowMode.SEND)


async def on_confirm_requisites(callback: CallbackQuery, widget: Any, dialog_manager: DialogManager) -> None:
    await callback.message.edit_text(f"{callback.message.text[:-1]}: <b>Да</b>")
    await callback.message.answer("Ожидайте выплату в ближайшее время, спасибо ☺")
    await dialog_manager.done()


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


async def on_close(_: dict[str, Any], dialog_manager: DialogManager) -> None:
    state = dialog_manager.middleware_data["state"]
    await state.clear()


async def mes_input_handler(message: Message, widget: MessageInput, dialog_manager: DialogManager) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]
    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if message.text == "stop":
        await dialog_manager.done()
        return

    await dialog_manager.show(ShowMode.SEND)


cashback_article_dialog = Dialog(
    Window(
        Format("Отправьте, пожалуйста, <b>скриншот</b> сделанного заказа"),
        MessageInput(on_input_order_screenshot, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_order,
    ),
    Window(
        Format(
            "📬 Когда получите <code>{article.title}</code>, отправьте, пожалуйста, <b>скриншот отзыва</b> на 5 звёзд"
        ),
        MessageInput(on_input_feedback_screenshot, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_received,
        getter=article_getter,
    ),
    Window(
        Format("✂ Разрежте этикетки (qr-код или штрихкод) и отправьте, пожалуйста, фотографию разрезанных этикеток"),
        MessageInput(on_input_cut_labels_photo, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_labels_cut,
    ),
    Window(
        Const(
            "Отправьте теперь нам, пожалуйста, свой номер телефона в формате:\n\n<code>+7910XXXXXXX</code>",
            # когда нет номера телефона, номера карты, суммы и банка
            when=lambda d, _, __: not any(((d["phone_number"] or d["card_number"]), d["amount"], d["bank"])),
        ),
        Const(
            "📩 Получены реквизиты:",
            # когда есть хотя бы один из: номер телефона, номер карты, сумма или банк
            when=lambda d, _, __: any(((d["phone_number"] or d["card_number"]), d["amount"], d["bank"])),
        ),
        Format("Номер карты: <code>{card_number}</code>", when=lambda d, _, __: d["card_number"]),
        Format("Номер телефона: <code>{phone_number}</code>", when=lambda d, _, __: d["phone_number"]),
        Format("Банк: <code>{bank}</code>", when=lambda d, _, __: d["bank"]),
        Format("Сумма: <code>{amount} ₽</code>", when=lambda d, _, __: d["amount"]),
        Const(" "),
        Const(
            "💬 Пожалуйста, отправьте название банка (например: <b>Сбербанк</b>, <b>Т-банк</b>)",
            # когда нет банка и есть сумма, или номер телефона, или номер карты
            when=lambda d, _, __: (not d["bank"]) and (d["amount"] or d["phone_number"] or d["card_number"]),
        ),
        Const(
            "💬 Пожалуйста, отправьте реквизиты для оплаты: номер телефона или номер банковской карты.",
            # когда нет номера телефона или карты и есть банк или сумма
            when=lambda d, _, __: (not (d["phone_number"] or d["card_number"])) and (d["bank"] or d["amount"]),
        ),
        Const(
            "💬 Пожалуйста, отправьте сумму перевода, например: 500 рублей",
            # когда нет суммы и есть банк или номер телефона, или номер карты
            when=lambda d, _, __: (not d["amount"]) and (d["bank"] or d["phone_number"] or d["card_number"]),
        ),
        Const(
            "Реквизиты заполнены верно?",
            # когда есть хотя все реквизиты: номер телефона, номер карты, сумма или банк
            when=lambda d, _, __: all(((d["phone_number"] or d["card_number"]), d["amount"], d["bank"])),
        ),
        Row(
            Button(
                Const("✅ Да, верно"),
                id="conf_requisites",
                on_click=on_confirm_requisites,
                when=lambda d, _, __: all(((d["phone_number"] or d["card_number"]), d["amount"], d["bank"])),
            ),
            Button(
                Const("❌ Не верно"),
                id="dec_requisites",
                on_click=on_decline_requisites,
                when=lambda d, _, __: all(((d["phone_number"] or d["card_number"]), d["amount"], d["bank"])),
            ),
        ),
        MessageInput(on_input_requisites),
        state=CashbackArticleStates.input_requisites,
        getter=requisites_getter,
    ),
    on_close=on_close,
)
