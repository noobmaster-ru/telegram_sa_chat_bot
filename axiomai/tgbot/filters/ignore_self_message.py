from aiogram import Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway


class SelfBusinessMessageFilter(BaseFilter):
    @inject
    async def __call__(self, message: Message, cabinet_gateway: FromDishka[CabinetGateway], bot: Bot) -> bool:
        business_connection = await bot.get_business_connection(message.business_connection_id)
        return message.from_user.id == business_connection.user.id
