from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats


async def setup(bot: Bot) -> None:
    await set_user_commands(bot)


async def set_user_commands(bot: Bot) -> None:
    commands = [
        BotCommand(
            command="start",
            description="Старт",
        ),
        BotCommand(
            command="disable_autopayments",
            description="Отключить автовыплаты (если включены)",
        ),
        BotCommand(
            command="enable_autopayments",
            description="Включить автовыплаты (если отключены)",
        ),
    ]
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeAllPrivateChats())
