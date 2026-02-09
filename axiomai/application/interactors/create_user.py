import logging

from axiomai.application.exceptions.cabinet import BusinessAccountAlreadyLinkedError, CabinetAlreadyExistsError
from axiomai.application.exceptions.user import UserAlreadyExistsError
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.models import User
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class CreateSeller:
    def __init__(
        self, user_gateway: UserGateway, cabinet_gateway: CabinetGateway, transaction_manager: TransactionManager
    ) -> None:
        self._user_gateway = user_gateway
        self._cabinet_gateway = cabinet_gateway
        self._transaction_manager = transaction_manager

    async def execute(
        self,
        telegram_id: int,
        user_name: str | None,
        fullname: str | None,
    ) -> None:
        cabinet = await self._cabinet_gateway.get_cabinet_by_telegram_id_or_business_account_id(telegram_id)

        if cabinet and cabinet.business_account_id == telegram_id:
            raise BusinessAccountAlreadyLinkedError
        if cabinet and cabinet.business_account_id != telegram_id:
            raise CabinetAlreadyExistsError

        user = await self._user_gateway.get_user_by_telegram_id(telegram_id)
        if user:
            raise UserAlreadyExistsError

        user = User(telegram_id=telegram_id, user_name=user_name, fullname=fullname, email=None)

        await self._user_gateway.create_user(user)

        await self._transaction_manager.commit()

        logger.info("user created with telegram_id = %s", telegram_id)
