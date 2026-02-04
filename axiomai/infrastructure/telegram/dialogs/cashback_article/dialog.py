from typing import Any

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const, Format
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from redis.asyncio import Redis

from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.telegram.dialogs.cashback_article.common import mes_input_handler
from axiomai.infrastructure.telegram.dialogs.cashback_article.q1_input_order_screenshot import on_input_order_screenshot
from axiomai.infrastructure.telegram.dialogs.cashback_article.q2_input_feedback_screenshot import (
    on_input_feedback_screenshot,
)
from axiomai.infrastructure.telegram.dialogs.cashback_article.q3_input_cut_labels_screenshot import (
    on_input_cut_labels_photo,
)
from axiomai.infrastructure.telegram.dialogs.cashback_article.q4_input_requisites import (
    on_confirm_requisites,
    on_decline_requisites,
    on_input_requisites,
)
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
async def on_close(
    _: dict[str, Any], dialog_manager: DialogManager, bot: FromDishka[Bot], redis: FromDishka[Redis]
) -> None:
    state = FSMContext(
        RedisStorage(redis, key_builder=DefaultKeyBuilder(with_destiny=True)),
        StorageKey(user_id=dialog_manager.event.from_user.id, chat_id=dialog_manager.event.from_user.id, bot_id=bot.id),
    )

    await state.clear()


cashback_article_dialog = Dialog(
    Window(
        Format("Отправьте, пожалуйста, <b>скриншот</b> сделанного заказа артикула <code>{article.nm_id}</code>"),
        MessageInput(on_input_order_screenshot, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_order,
        getter=article_getter,
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
            # когда есть все реквизиты: номер телефона, номер карты, сумма или банк
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
