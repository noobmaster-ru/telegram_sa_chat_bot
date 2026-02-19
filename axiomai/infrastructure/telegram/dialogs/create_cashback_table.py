from typing import Any

from aiogram import Bot
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Const
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from axiomai.application.exceptions.cashback_table import CashbackTableAlredyExistsError
from axiomai.application.interactors.create_cashback_table import CreateCashbackTable
from axiomai.config import Config
from axiomai.constants import GOOGLE_SHEETS_TEMPLATE_URL
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.dialogs.states import CreateCashbackTableStates, RefillBalanceStates


@inject
async def input_gs_link(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    link: str,
    create_cashback_table: FromDishka[CreateCashbackTable],
    config: FromDishka[Config],
) -> None:
    if link == GOOGLE_SHEETS_TEMPLATE_URL:
        await message.answer("Пожалуйста, отправьте ссылку на <b>СВОЮ</b> таблицу!")
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    if not link.startswith("https://docs.google.com/spreadsheets/") and not link.startswith(
        "docs.google.com/spreadsheets/"
    ):
        await message.answer("Пожалуйста, пришлите ссылку на гугл-таблицу (без других слов)")
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    try:
        part1 = link.rsplit("/d/", maxsplit=1)[-1]
        table_id = part1.split("/edit")[0]
    except IndexError:
        await message.answer("Пожалуйста, пришлите корректную ссылку на гугл-таблицу")
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    try:
        await create_cashback_table.execute(message.from_user.id, table_id)
    except CashbackTableAlredyExistsError:
        await message.answer("Таблица с такими данными уже существует в нашей системе.")
        dialog_manager.show_mode = ShowMode.NO_UPDATE
        return

    await send_insctruction_message(dialog_manager.middleware_data["bot"], message.chat.id, config)
    await dialog_manager.done()


async def send_insctruction_message(bot: Bot, chat_id: int, config: Config) -> None:
    caption = (
        "Теперь <b>внимательно!</b>\n\n"
        "Добавьте сервисный аккаунт в Google-таблицу, "
        "без добавления мы не сможем записывать данные в вашу таблицу.\n\n"
        "Вот подробная инструкция:\n"
        "1. Откройте свою таблицу\n"
        "2. В правом верхнем углу откройте настройки доступа <b>(фото1)</b>\n"
        "3. В поисковой строке вбейте вот этот email <b>(фото2)</b>:\n\n"
        f"<b>{config.service_account_axiomai_email}</b>\n\n"
        "4. Дайте доступ <b>Редактор</b> этому сервисному аккаунту Google <b>(фото3)</b>\n\n"
        "Как сделаете, у вас должно получиться вот так, как на <b>(фото4)</b>"
    )

    media_group = [
        InputMediaPhoto(
            media=FSInputFile("./assets/reg_photos/1_access_settings.png"),
            caption=caption,
        ),
        InputMediaPhoto(media=FSInputFile("./assets/reg_photos/2_search_bar.png")),
        InputMediaPhoto(media=FSInputFile("./assets/reg_photos/3_access_axiomai_editor.png")),
        InputMediaPhoto(media=FSInputFile("./assets/reg_photos/4_axiomai_service_account.png")),
    ]
    await bot.send_media_group(chat_id=chat_id, media=media_group)


@inject
async def on_superbanking_yes(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    cabinet_gateway: FromDishka[CabinetGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    cabinet = await cabinet_gateway.get_cabinet_by_telegram_id(callback.from_user.id)
    if cabinet:
        cabinet.is_superbanking_connect = True
        await transaction_manager.commit()

    text = callback.message.text.replace("Подключать автовыплаты?", "Подключать автовыплаты: <b>Да</b>")
    await callback.message.edit_text(text)
    await dialog_manager.next(show_mode=ShowMode.NO_UPDATE)
    await dialog_manager.start(RefillBalanceStates.waiting_for_amount, show_mode=ShowMode.SEND)


async def on_superbanking_no(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    text = callback.message.text.replace("Подключать автовыплаты?", "Подключать автовыплаты: <b>Нет</b>")
    await callback.message.edit_text(text)
    await callback.answer("Хорошо, автовыплаты не подключены. Вы можете подключить их позже.", show_alert=True)
    await dialog_manager.next(show_mode=ShowMode.SEND)


create_cashback_table_dialog = Dialog(
    Window(
        Const(
            "Подключать автовыплаты?\n\n"
            "<code>P.S. Автовыплаты - это когда деньги за кешбэк автоматически перечисляются на карту клиента.</code>"
        ),
        Row(
            Button(Const("✅ Да"), id="superbanking_yes", on_click=on_superbanking_yes),
            Button(Const("❌ Нет"), id="superbanking_no", on_click=on_superbanking_no),
        ),
        state=CreateCashbackTableStates.ask_superbanking,
    ),
    Window(
        Const(
            "Сделайте себе копию этой таблицы\n\n"
            f"{GOOGLE_SHEETS_TEMPLATE_URL}\n\n"
            "вставьте в ячейку B2 ссылку на ваш артикул, подождите пока подгрузятся данные c сайта ВБ и пришлите мне <b>ссылку на таблицу</b>"
        ),
        TextInput(id="gs_link", on_success=input_gs_link),
        state=CreateCashbackTableStates.copy_gs_template,
    ),
)
