import pytest
from sqlalchemy import select

from axiomai.application.interactors.create_user import CreateSeller
from axiomai.infrastructure.database.models import User


@pytest.fixture
async def create_seller(di_container) -> CreateSeller:
    return await di_container.get(CreateSeller)


async def test_create_seller(create_seller, session):
    telegram_id = 123456789

    await create_seller.execute(telegram_id, user_name=None, fullname=None)

    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    assert user.telegram_id == telegram_id
