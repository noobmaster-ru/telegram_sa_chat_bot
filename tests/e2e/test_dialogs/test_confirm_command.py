from unittest.mock import AsyncMock, Mock

from sqlalchemy import select

from axiomai.infrastructure.database.models import Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.openai import OpenAIGateway
from tests.e2e.conftest import cashback_table_factory, cashback_article_factory
from tests.e2e.test_dialogs.conftest import FakeBotClient, FakeBot

SELLER_USER_ID = 9999  # продавец
LEAD_USER_ID = 1       # лид (дефолтный user_id FakeBotClient)

async def _start_dialog(bot_client: FakeBotClient, article, openai_gateway) -> None:
    """Запускает диалог с лидом и создаёт buyer."""
    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление кешбека.",
        "article_ids": [article.id],
    })
    await bot_client.send_business("хочу кешбек")


async def test_confirm_single_buyer_order_no_amount(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """
    /confirm — одна заявка на шаге заказа, amount не указан.
    buyer.is_ordered = True, buyer.amount остаётся None.
    """
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    await _start_dialog(bot_client, article, openai_gateway)

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business("/confirm")

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_ordered is True
    assert buyer.amount is None
    assert len(fake_bot.deleted_business_messages) == 1


async def test_confirm_single_buyer_order_with_amount(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/confirm 1500 — одна заявка на шаге заказа, amount записывается в buyer."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    await _start_dialog(bot_client, article, openai_gateway)

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business("/confirm 1500")

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_ordered is True
    assert buyer.amount == 1500


async def test_confirm_single_buyer_feedback(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/confirm на шаге отзыва → buyer.is_left_feedback = True."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    await _start_dialog(bot_client, article, openai_gateway)

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )

    # Сначала подтверждаем заказ
    await seller_client.send_business("/confirm")
    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_ordered is True

    # Теперь подтверждаем отзыв
    await seller_client.send_business("/confirm")
    assert buyer.is_left_feedback is True


async def test_confirm_single_buyer_labels(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/confirm на шаге этикеток → buyer.is_cut_labels = True."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    await _start_dialog(bot_client, article, openai_gateway)

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )

    await seller_client.send_business("/confirm")  # order
    await seller_client.send_business("/confirm")  # feedback
    await seller_client.send_business("/confirm")  # labels

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_cut_labels is True


async def test_confirm_multiple_buyers_requires_nm_id(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """
    Если заявок несколько и nm_id не указан — /confirm ничего не делает.
    """
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.",
        "article_ids": [article1.id, article2.id],
    })
    await bot_client.send_business("хочу кешбек")

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business("/confirm")  # без nm_id

    buyers = (await session.scalars(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))).all()
    assert all(not b.is_ordered for b in buyers)


async def test_confirm_multiple_buyers_with_nm_id(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/confirm {nm_id} подтверждает только конкретную заявку."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.",
        "article_ids": [article1.id, article2.id],
    })
    await bot_client.send_business("хочу кешбек")

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business(f"/confirm {article1.nm_id}")

    buyer1 = await session.scalar(select(Buyer).where(
        Buyer.telegram_id == LEAD_USER_ID, Buyer.nm_id == article1.nm_id
    ))
    buyer2 = await session.scalar(select(Buyer).where(
        Buyer.telegram_id == LEAD_USER_ID, Buyer.nm_id == article2.nm_id
    ))
    assert buyer1.is_ordered is True
    assert buyer2.is_ordered is False


async def test_confirm_multiple_buyers_with_nm_id_and_amount(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/confirm {nm_id} {amount} записывает amount только в нужного buyer."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.",
        "article_ids": [article1.id, article2.id],
    })
    await bot_client.send_business("хочу кешбек")

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business(f"/confirm {article1.nm_id} 2500")

    buyer1 = await session.scalar(select(Buyer).where(
        Buyer.telegram_id == LEAD_USER_ID, Buyer.nm_id == article1.nm_id
    ))
    buyer2 = await session.scalar(select(Buyer).where(
        Buyer.telegram_id == LEAD_USER_ID, Buyer.nm_id == article2.nm_id
    ))
    assert buyer1.is_ordered is True
    assert buyer1.amount == 2500
    assert buyer2.is_ordered is False
    assert buyer2.amount is None


async def test_confirm_from_lead_is_ignored(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/confirm от лида (не продавца) не должна ничего делать."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "не понял",
        "wants_to_stop": False,
        "switch_to_article_id": None,
    })

    await _start_dialog(bot_client, article, openai_gateway)

    # Лид сам пишет /confirm
    await bot_client.send_business("/confirm")

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_ordered is False


async def test_cancel_cancels_buyer(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/cancel {nm_id} — продавец отменяет заявку лида → buyer.is_canceled=True."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    await _start_dialog(bot_client, article, openai_gateway)

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business(f"/cancel {article.nm_id}")

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_canceled is True
    assert len(fake_bot.deleted_business_messages) == 1


async def test_cancel_requires_nm_id(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/cancel без nm_id при одном buyer отменяет его."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    await _start_dialog(bot_client, article, openai_gateway)

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business("/cancel")

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_canceled is True


async def test_cancel_without_nm_id_requires_it_when_multiple_buyers(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/cancel без nm_id при нескольких buyer ничего не делает."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.",
        "article_ids": [article1.id, article2.id],
    })
    await bot_client.send_business("хочу кешбек")

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business("/cancel")

    buyers = (await session.scalars(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))).all()
    assert all(not b.is_canceled for b in buyers)


async def test_cancel_already_ordered_buyer_does_nothing(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/cancel {nm_id} для заявки с is_ordered=True ничего не меняет."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    await _start_dialog(bot_client, article, openai_gateway)

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    # Сначала подтверждаем заказ
    await seller_client.send_business("/confirm")

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == LEAD_USER_ID))
    assert buyer.is_ordered is True

    # Теперь пытаемся отменить — уже нельзя
    await seller_client.send_business(f"/cancel {article.nm_id}")

    await session.refresh(buyer)
    assert buyer.is_canceled is False
    assert buyer.is_ordered is True


async def test_cancel_one_of_two_buyers(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """/cancel {nm_id} отменяет только указанную заявку из двух."""
    fake_bot.get_business_connection = AsyncMock(return_value=Mock(user=Mock(id=SELLER_USER_ID)))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.",
        "article_ids": [article1.id, article2.id],
    })
    await bot_client.send_business("хочу кешбек")

    seller_client = FakeBotClient(
        bot_client.dp,
        user_id=SELLER_USER_ID,
        chat_id=LEAD_USER_ID,
        business_connection_id=bot_client.business_connection_id,
        bot=fake_bot,
    )
    await seller_client.send_business(f"/cancel {article1.nm_id}")

    buyer1 = await session.scalar(select(Buyer).where(
        Buyer.telegram_id == LEAD_USER_ID, Buyer.nm_id == article1.nm_id
    ))
    buyer2 = await session.scalar(select(Buyer).where(
        Buyer.telegram_id == LEAD_USER_ID, Buyer.nm_id == article2.nm_id
    ))
    assert buyer1.is_canceled is True
    assert buyer2.is_canceled is False
