from sqlalchemy import select

from axiomai.infrastructure.database.gateways.base import Gateway
from axiomai.infrastructure.database.models import Cabinet, User


class UserGateway(Gateway):
    async def create_user(self, user: User) -> None:
        self._session.add(user)
        await self._session.flush()

    async def get_user_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self._session.scalar(select(User).where(User.telegram_id == telegram_id))

    async def get_user_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_user_by_cabinet_id(self, cabinet_id: int) -> User | None:
        return await self._session.scalar(select(User).join(Cabinet).where(Cabinet.id == cabinet_id))
