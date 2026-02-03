from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message


class SelfBusinessMessageFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        business_connection = await bot.get_business_connection(message.business_connection_id)
        return message.from_user.id == business_connection.user.id
