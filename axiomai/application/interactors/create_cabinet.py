import secrets

from axiomai.application.exceptions.cabinet import CabinetAlreadyExistsError
from axiomai.application.exceptions.user import UserNotFoundError
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.models import Cabinet
from axiomai.infrastructure.database.transaction_manager import TransactionManager


class CreateCabinet:
    def __init__(
        self, user_gateway: UserGateway, cabinet_gateway: CabinetGateway, transaction_manager: TransactionManager
    ) -> None:
        self._user_gateway = user_gateway
        self._cabinet_gateway = cabinet_gateway
        self._transaction_manager = transaction_manager

    async def execute(self, telegram_id: int) -> None:
        user = await self._user_gateway.get_user_by_telegram_id(telegram_id)
        if not user:
            raise UserNotFoundError(f"User by telegram id {telegram_id} not found")

        cabinet = await self._cabinet_gateway.get_cabinet_by_telegram_id(telegram_id)
        if cabinet:
            raise CabinetAlreadyExistsError

        link_code = secrets.token_urlsafe(16)
        cabinet = Cabinet(
            user_id=user.id,
            organization_name="none",
            leads_balance=0,
            link_code=link_code,
        )
        await self._cabinet_gateway.create_cabinet(cabinet)

        await self._transaction_manager.commit()
