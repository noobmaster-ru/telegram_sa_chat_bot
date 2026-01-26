import logging

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.application.exceptions.cashback_table import CashbackTableAlredyExistsError
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.models import CashbackTable
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.database.transaction_manager import TransactionManager

logger = logging.getLogger(__name__)


class CreateCashbackTable:
    def __init__(
        self,
        cashback_table_gateway: CashbackTableGateway,
        cabinet_gateway: CabinetGateway,
        transation_manager: TransactionManager,
    ) -> None:
        self._cashback_table_gateway = cashback_table_gateway
        self._cabinet_gateway = cabinet_gateway
        self._tranasction_manager = transation_manager

    async def execute(self, telegram_id: int, table_id: str) -> None:
        cabinet = await self._cabinet_gateway.get_cabinet_by_telegram_id(telegram_id)
        if not cabinet:
            raise CabinetNotFoundError(f"Cabinet not found for telegram_id {telegram_id}")

        cashback_table = await self._cashback_table_gateway.get_cashback_table_by_table_id(table_id)
        if cashback_table:
            raise CashbackTableAlredyExistsError

        cashback_table = CashbackTable(cabinet_id=cabinet.id, table_id=table_id, status=CashbackTableStatus.NEW)
        await self._cashback_table_gateway.create_cashback_table(cashback_table)
        await self._tranasction_manager.commit()

        logger.info("cashback table created for cabinet_id=%s, table_id=%s", cabinet.id, table_id)
