from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode, ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Format, Const
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.telegram.dialogs.states import CashbackArticleStates


async def instruction_getter(dialog_manager: DialogManager, **kwargs: dict[str, Any]) -> dict[str, Any]:
    start_data = dialog_manager.start_data or {}
    instruction_text = start_data.get("instruction_text")
    nm_id = start_data.get("nm_id")
    article_title = start_data.get("article_title")

    return {
        "instruction_text": instruction_text,
        "nm_id": nm_id,
        "article_title": article_title,
    }


async def on_agree_clicked(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    await callback.message.answer("Спасибо за согласие с нашими условиями!")
    await dialog_manager.next(ShowMode.SEND)


async def on_disagree_clicked(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    await callback.message.answer("Вы не согласились с условиями")
    await dialog_manager.done()


async def on_order_confirmed(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    await callback.message.edit_reply_markup()
    await callback.message.answer("Отправьте, пожалуйста, <b>скриншот</b> сделанного заказа")
    dialog_manager.show_mode = ShowMode.NO_UPDATE


async def on_order_declined(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    article_title = dialog_manager.start_data.get("article_title")

    await callback.message.answer(
        f"Когда закажете товар <code>{article_title}</code>, нажмите, пожалуйста, на кнопку ниже"
    )
    dialog_manager.show_mode = ShowMode.SEND


@inject
async def on_input_order_screenshot(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото скриншота заказа")
        return

    bot: Bot = dialog_manager.middleware_data.get("bot")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    start_data = dialog_manager.start_data or {}
    article_title = start_data.get("article_title")
    brand_name = start_data.get("brand_name")
    article_image_url = start_data.get("article_image_url")

    await message.answer("⏳ Проверяю скриншот заказа...")

    result = await openai_gateway.classify_order_screenshot(photo_url, article_title, brand_name, article_image_url)

    if not result["is_order"]:
        await message.answer(
            "❌ Заказ не найден на скриншоте\n\n" "Пожалуйста, отправьте корректный скриншот заказа из Wildberries"
        )
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await message.answer("✅ Скриншот заказа принят!")
    await dialog_manager.next(ShowMode.SEND)


async def on_received_yes(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    await callback.message.edit_reply_markup()
    await callback.message.answer("Отправьте, пожалуйста, скриншот отзыва на 5 звёзд")
    dialog_manager.show_mode = ShowMode.NO_UPDATE


async def on_received_no(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    article_title = dialog_manager.start_data.get("article_title")

    await callback.message.answer(f"Когда оставите отзыв на товар {article_title}, нажмите, пожалуйста, на кнопку ниже")
    dialog_manager.show_mode = ShowMode.SEND


@inject
async def on_input_feedback_screenshot(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    openai_gateway: FromDishka[OpenAIGateway],
) -> None:
    bot: Bot = dialog_manager.middleware_data["bot"]

    await bot.read_business_message(message.business_connection_id, message.chat.id, message.message_id)

    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото скриншота отзыва")
        return

    bot: Bot = dialog_manager.middleware_data.get("bot")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    start_data = dialog_manager.start_data or {}
    article_title = start_data.get("article_title")
    brand_name = start_data.get("brand_name")

    await message.answer("⏳ Проверяю скриншот отзыва...")

    result = await openai_gateway.classify_feedback_screenshot(photo_url, article_title, brand_name)

    if not result["is_feedback"]:
        await message.answer(
            "❌ Отзыв не найден на скриншоте\n\n" "Пожалуйста, отправьте корректный скриншот отзыва с 5 звёздами"
        )
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await message.answer("✅ Скриншот отзыва принят!")
    await dialog_manager.next(ShowMode.SEND)


async def on_labels_cut_yes(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    await callback.message.edit_reply_markup()
    await callback.message.answer("Отправьте, пожалуйста, фотографию разрезанных этикеток")
    dialog_manager.show_mode = ShowMode.NO_UPDATE


async def on_labels_cut_no(callback: CallbackQuery, button: Button, dialog_manager: DialogManager) -> None:
    article_title = dialog_manager.start_data.get("article_title")

    await callback.message.answer(f"Когда разрежете этикетки от {article_title}, нажмите, пожалуйста, на кнопку ниже")
    dialog_manager.show_mode = ShowMode.SEND


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

    bot: Bot = dialog_manager.middleware_data.get("bot")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    await message.answer("⏳ Проверяю фотографию разрезанных этикеток...")

    result = await openai_gateway.classify_cut_labels_photo(photo_url)

    if not result["is_cut_labels"]:
        await message.answer(
            "❌ Фото разрезанных штрихкодов не принято. Пожалуйста, разрежьте этикетки и пришлите фото ещё раз☺️"
        )
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await message.answer("✅ Фотография разрезанных этикеток принята!")
    await message.answer("☺️ Вы прислали все фотографии, которые были нам нужны. Спасибо!")
    await message.answer(
        "Отправьте теперь нам, пожалуйста, свой номер телефона в формате:\n\n*+7910XXXXXXX*\n\nСпасибо"
    )
    dialog_manager.show_mode = ShowMode.NO_UPDATE


async def on_close(_, dialog_manager: DialogManager) -> None:
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
        Format("{instruction_text}"),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.show_instruction,
        getter=instruction_getter,
        parse_mode=ParseMode.MARKDOWN_V2,
    ),
    Window(
        Const("Здравствуйте! Я - 🤖-помощник.\n" "Вы согласны на наши условия кэшбека?"),
        Row(
            Button(Const("✅ Да, согласен(на)"), id="agree", on_click=on_agree_clicked),
            Button(Const("❌ Не согласен"), id="disagree", on_click=on_disagree_clicked),
        ),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.agreement_terms,
    ),
    Window(
        Format("📦 Вы заказали <code>{article_title}</code>?"),
        Row(
            Button(Const("✅ Да, заказал(а)"), id="order_yes", on_click=on_order_confirmed),
            Button(Const("❌ Не заказал(а)"), id="order_no", on_click=on_order_declined),
        ),
        MessageInput(on_input_order_screenshot, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_order,
        getter=instruction_getter,
    ),
    Window(
        Format("📬 Когда получите {article_title}, нажмите на кнопку `Да, получил(a)` ниже"),
        Row(
            Button(Const("✅ Да, получил(а)"), id="received_yes", on_click=on_received_yes),
            Button(Const("❌ Нет"), id="received_no", on_click=on_received_no),
        ),
        MessageInput(on_input_feedback_screenshot, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_received,
        getter=instruction_getter,
    ),
    Window(
        Format("✂️ Этикетки разрезали на {article_title}?"),
        Row(
            Button(Const("✅ Да, разрезал(а)"), id="labels_cut_yes", on_click=on_labels_cut_yes),
            Button(Const("❌ Нет"), id="labels_cut_no", on_click=on_labels_cut_no),
        ),
        MessageInput(on_input_cut_labels_photo, content_types=[ContentType.PHOTO]),
        MessageInput(mes_input_handler),
        state=CashbackArticleStates.check_labels_cut,
        getter=instruction_getter,
    ),
    on_close=on_close,
)
