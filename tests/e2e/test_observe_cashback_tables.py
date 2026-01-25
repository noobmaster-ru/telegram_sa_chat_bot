from unittest.mock import AsyncMock

import pytest

from axiomai.application.exceptions.cashback_table import WritePermissionError
from axiomai.application.interactors.observe_cashback_tables import ObserveCashbackTables
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus


@pytest.fixture
async def observe_cashback_tables(di_container) -> ObserveCashbackTables:
    return await di_container.get(ObserveCashbackTables)


async def test_observe_cashback_tables(cashback_table_factory, observe_cashback_tables) -> None:
    cashback_table = await cashback_table_factory()

    await observe_cashback_tables.execute()
    await observe_cashback_tables.execute()
    await observe_cashback_tables.execute()

    assert cashback_table.status == CashbackTableStatus.VERIFIED
    observe_cashback_tables._bot.send_message.assert_awaited_once()


async def test_observe_cashback_tables_with_permisson_error(cashback_table_factory, observe_cashback_tables) -> None:
    cashback_table = await cashback_table_factory()

    observe_cashback_tables._google_sheets_gateway.ensure_service_account_added = AsyncMock(side_effect=PermissionError)

    await observe_cashback_tables.execute()
    await observe_cashback_tables.execute()
    await observe_cashback_tables.execute()

    assert cashback_table.status == CashbackTableStatus.NEW
    observe_cashback_tables._bot.send_message.assert_not_awaited()


async def test_observe_cashback_tables_with_write_permisson_error(
    cashback_table_factory, observe_cashback_tables
) -> None:
    cashback_table = await cashback_table_factory()

    observe_cashback_tables._google_sheets_gateway.ensure_service_account_added.side_effect = AsyncMock(
        side_effect=WritePermissionError
    )

    await observe_cashback_tables.execute()
    await observe_cashback_tables.execute()
    await observe_cashback_tables.execute()

    assert cashback_table.status == CashbackTableStatus.WAITING_WRITE_PERMISSION
    observe_cashback_tables._bot.send_message.assert_awaited_once()
