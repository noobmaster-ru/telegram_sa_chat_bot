from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from axiomai.application.dto import CashbackArticle as CashbackArticleDTO
from axiomai.application.interactors.sync_cashback_tables import SyncCashbackTables
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus, CashbackArticle


@pytest.fixture
async def sync_cashback_tables(di_container) -> SyncCashbackTables:
    return await di_container.get(SyncCashbackTables)


async def test_sync_cashback_tables_creates_articles(
    cashback_table_factory, sync_cashback_tables, session: AsyncSession
) -> None:
    cashback_table = await cashback_table_factory(status=CashbackTableStatus.VERIFIED)

    articles_dto = [
        CashbackArticleDTO(nm_id=123, title="Product 1", brand_name="Brand A", instruction_text="Instruction 1", image_url="http://img1.jpg", in_stock=True),
        CashbackArticleDTO(nm_id=456, title="Product 2", brand_name="Brand B", instruction_text="Instruction 2", image_url="http://img2.jpg", in_stock=False),
    ]
    sync_cashback_tables._google_sheets_gateway.get_cashback_articles = AsyncMock(return_value=articles_dto)

    await sync_cashback_tables.execute()

    articles = list(await session.scalars(select(CashbackArticle).where(CashbackArticle.cabinet_id == cashback_table.cabinet_id)))
    assert len(articles) == 2
    assert {a.nm_id for a in articles} == {123, 456}
    assert cashback_table.last_synced_at is not None


async def test_sync_cashback_tables_updates_last_synced_at(
    cashback_table_factory, sync_cashback_tables
) -> None:
    cashback_table = await cashback_table_factory(status=CashbackTableStatus.PAID)
    assert cashback_table.last_synced_at is None

    sync_cashback_tables._google_sheets_gateway.get_cashback_articles = AsyncMock(return_value=[])

    await sync_cashback_tables.execute()

    assert cashback_table.last_synced_at is not None


async def test_sync_cashback_tables_deletes_removed_articles(
    cashback_table_factory, sync_cashback_tables, session: AsyncSession
) -> None:
    cashback_table = await cashback_table_factory(status=CashbackTableStatus.VERIFIED)

    old_article = CashbackArticle(
        cabinet_id=cashback_table.cabinet_id,
        nm_id=999,
        title="Old Product",
        brand_name="Old Brand",
        instruction_text="Old Instruction",
        image_url="http://old.jpg",
        in_stock=True,
    )
    session.add(old_article)
    await session.flush()

    new_articles_dto = [
        CashbackArticleDTO(nm_id=111, title="New Product", brand_name="New Brand", instruction_text="New Instruction", image_url="http://new.jpg", in_stock=True),
    ]
    sync_cashback_tables._google_sheets_gateway.get_cashback_articles = AsyncMock(return_value=new_articles_dto)

    await sync_cashback_tables.execute()

    articles = list(await session.scalars(select(CashbackArticle).where(CashbackArticle.cabinet_id == cashback_table.cabinet_id)))
    assert len(articles) == 1
    assert articles[0].nm_id == 111


async def test_sync_cashback_tables_updates_existing_articles(
    cashback_table_factory, sync_cashback_tables, session: AsyncSession
) -> None:
    cashback_table = await cashback_table_factory(status=CashbackTableStatus.VERIFIED)

    existing_article = CashbackArticle(
        cabinet_id=cashback_table.cabinet_id,
        nm_id=123,
        title="Old Title",
        brand_name="Old Brand",
        instruction_text="Old Instruction",
        image_url="http://old.jpg",
        in_stock=False,
    )
    session.add(existing_article)
    await session.flush()
    article_id = existing_article.id

    updated_dto = [
        CashbackArticleDTO(nm_id=123, title="New Title", brand_name="New Brand", instruction_text="New Instruction", image_url="http://new.jpg", in_stock=True),
    ]
    sync_cashback_tables._google_sheets_gateway.get_cashback_articles = AsyncMock(return_value=updated_dto)

    await sync_cashback_tables.execute()

    articles = list(await session.scalars(select(CashbackArticle).where(CashbackArticle.cabinet_id == cashback_table.cabinet_id)))
    assert len(articles) == 1
    assert articles[0].id == article_id
    assert articles[0].nm_id == 123
    assert articles[0].title == "New Title"
    assert articles[0].brand_name == "New Brand"
    assert articles[0].instruction_text == "New Instruction"
    assert articles[0].image_url == "http://new.jpg"


async def test_sync_cashback_tables_skips_inactive_tables(
    cashback_table_factory, sync_cashback_tables
) -> None:
    cashback_table = await cashback_table_factory(status=CashbackTableStatus.NEW)

    sync_cashback_tables._google_sheets_gateway.get_cashback_articles = AsyncMock(return_value=[])

    await sync_cashback_tables.execute()

    sync_cashback_tables._google_sheets_gateway.get_cashback_articles.assert_not_awaited()
    assert cashback_table.last_synced_at is None


async def test_sync_cashback_tables_continues_on_error(
    cashback_table_factory, sync_cashback_tables, session: AsyncSession
) -> None:
    table1 = await cashback_table_factory(status=CashbackTableStatus.VERIFIED)
    table2 = await cashback_table_factory(status=CashbackTableStatus.VERIFIED)

    call_count = 0

    async def mock_get_articles(table_id: str):
        nonlocal call_count
        call_count += 1
        if table_id == table1.table_id:
            raise Exception("API error")
        return [CashbackArticleDTO(nm_id=777, title="Product", brand_name="Brand", instruction_text="Instr", image_url="http://img.jpg", in_stock=True)]

    sync_cashback_tables._google_sheets_gateway.get_cashback_articles = mock_get_articles

    await sync_cashback_tables.execute()

    assert call_count == 2
    assert table1.last_synced_at is None
    assert table2.last_synced_at is not None

    articles = list(await session.scalars(select(CashbackArticle).where(CashbackArticle.cabinet_id == table2.cabinet_id)))
    assert len(articles) == 1
