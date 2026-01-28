import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import BusinessConnection, Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart(deep_link=True, magic=F.args.startswith("link_")))
@inject
async def cmd_link_business_account(
    message: Message,
    command: CommandObject,
    cabinet_gateway: FromDishka[CabinetGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    """Хендлер для подключения бизнес-аккаунта через deep link."""
    # Извлекаем код из deep link
    args = message.text.split(" ", 1)
    min_args_len = 2
    if len(args) < min_args_len or not args[1].startswith("link_"):
        await message.answer("❌ Неверная ссылка для подключения.")
        return

    link_code = args[1][5:]  # Убираем префикс "link_"

    # Находим кабинет по коду
    cabinet = await cabinet_gateway.get_cabinet_by_link_code(link_code)
    if not cabinet:
        await message.answer("❌ Код для подключения не найден или уже использован.")
        return

    # Сохраняем business_account_id и удаляем использованный link_code
    cabinet.business_account_id = message.from_user.id
    cabinet.link_code = None
    await transaction_manager.commit()

    await message.answer(
        "✅ Бизнес-аккаунт успешно связан с кабинетом!\n"
        "Теперь бот сможет автоматически обрабатывать сообщения от клиентов.\n\n"
        "<b>P.S. Также добавьте этого бота с правами управление сообщений в настройках бизнес-аккаунта в телеграмме</b>"
    )

    logger.info("business account %s linked to cabinet_id=%s", message.from_user.id, cabinet.id)


@router.business_connection(F.is_enabled)
@inject
async def enable_business_connection_handler(
    business_connection: BusinessConnection,
    bot: Bot,
    cabinet_gateway: FromDishka[CabinetGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    if not all(
        (
            business_connection.rights.can_reply,
            business_connection.rights.can_read_messages,
            business_connection.rights.can_delete_sent_messages,
        )
    ):
        await bot.send_message(
            business_connection.user.id,
            "❗ Пожалуйста, предоставьте боту все права из списка ниже\n"
            "- Чтение сообщений\n"
            "- Ответ на сообщения\n"
            "- Отметки о прочтении\n"
            "- Удаление исходящих\n\n"
            "чтобы он мог корректно работать с вашим бизнес-аккаунтом.",
        )
        return

    cabinet = await cabinet_gateway.get_cabinet_by_telegram_id_or_business_account_id(business_connection.user.id)
    if not cabinet:
        await bot.send_message(
            business_connection.user.id,
            "❗ Ваш бизнес-аккаунт не связан ни с одним кабинетом.\n"
            "Пожалуйста, создайте кабинет или свяжите его с существующим.",
        )
        return

    cabinet.business_connection_id = business_connection.id
    await transaction_manager.commit()

    await bot.send_message(business_connection.user.id, "✅ Бизнес-аккаунт успешно подключен и готов к работе!")


@router.business_connection(~F.is_enabled)
@inject
async def disable_business_connection_handler(
    business_connection: BusinessConnection,
    bot: Bot,
    cabinet_gateway: FromDishka[CabinetGateway],
    transaction_manager: FromDishka[TransactionManager],
) -> None:
    cabinet = await cabinet_gateway.get_cabinet_by_business_account_id(business_connection.user.id)

    cabinet.business_connection_id = None
    await transaction_manager.commit()

    await bot.send_message(
        business_connection.user.id,
        "⚠️ Бизнес-аккаунт отключен от бота. Чтобы возобновить работу, подключите его снова через настройки телеграмм.",
    )
