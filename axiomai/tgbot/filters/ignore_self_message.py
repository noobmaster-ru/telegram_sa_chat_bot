from aiogram.filters import BaseFilter
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway


class SelfBusinessMessageFilter(BaseFilter):
    @inject
    async def __call__(self, message: Message, cabinet_gateway: FromDishka[CabinetGateway]) -> bool:
        return bool(await cabinet_gateway.get_cabinet_by_business_account_id(message.from_user.id))
