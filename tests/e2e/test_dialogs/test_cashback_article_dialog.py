from unittest.mock import AsyncMock, Mock

from aiogram_dialog.test_tools import MockMessageManager
from aiogram_dialog.test_tools.keyboard import InlineButtonTextLocator
from sqlalchemy import select

from axiomai.infrastructure.database.models import Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.superbanking import Superbanking
from tests.e2e.conftest import cashback_table_factory, cashback_article_factory
from tests.e2e.test_dialogs.conftest import FakeBotClient, FakeBot


async def test_cashback_article_dialog_when_cabinet_not_found(bot_client: FakeBotClient, fake_bot: FakeBot):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))

    await bot_client.send_business("хочу кешбек")

    last_message = fake_bot.sent_messages[-1]
    assert last_message.text == "Таблица кешбека не найдена или не активна."


async def test_cashback_article_dialog_when_article_not_found(
    cabinet_factory,
    cashback_table_factory,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)

    await bot_client.send_business("хочу кешбек")

    last_message = fake_bot.sent_messages[-1]
    assert last_message.text == "Увы, артикулы для раздачи кэшбека закончились."


async def test_cashback_article_when_not_classified_message(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Здравствуйте! У нас есть товары для кешбека.",
        "article_id": None,
    })

    await bot_client.send_business("хочу кешбек")

    last_message = fake_bot.sent_messages[-1]
    assert "Здравствуйте" in last_message.text


async def test_cashback_article_filters_already_bought_articles(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article_bought = await cashback_article_factory(cabinet_id=cabinet.id)
    article_other = await cashback_article_factory(cabinet_id=cabinet.id)

    article_bought.nm_id = 111
    article_other.nm_id = 222
    await session.flush()

    buyer = Buyer(
        cabinet_id=cabinet.id,
        username=None,
        fullname="Test User",
        telegram_id=bot_client.user.id,
        nm_id=article_bought.nm_id,
    )
    session.add(buyer)
    await session.flush()

    openai_gateway = await di_container.get(OpenAIGateway)
    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Здравствуйте! У нас есть товары для кешбека.",
        "article_id": None,
    })

    await bot_client.send_business("хочу кешбек")

    called_args, called_kwargs = openai_gateway.chat_with_client.call_args
    articles_arg = called_kwargs.get("articles", called_args[1] if len(called_args) > 1 else None)
    assert articles_arg is not None
    assert {article.nm_id for article in articles_arg} == {article_other.nm_id}


async def test_cashback_article_q1_input_order_screenshot(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_id": article.id,
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={"is_order": True, "price": 1500})
    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    last_message = fake_bot.sent_messages[-1]
    assert last_message.text == "✅ Скриншот заказа принят!"
    assert buyer.is_ordered is True


async def test_cashback_article_q2_input_feedback_screenshot(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_id": article.id,
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={"is_order": True, "price": 1500})
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={"is_feedback": True})

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order
    await bot_client.send_business_photo()  # feedback

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    last_message = fake_bot.sent_messages[-1]
    assert last_message.text == "✅ Скриншот отзыва принят!"
    assert buyer.is_left_feedback is True


async def test_cashback_article_q3_input_cut_labels_screenshot(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_id": article.id,
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={"is_order": True, "price": 1500})
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={"is_feedback": True})
    openai_gateway.classify_cut_labels_screenshot = AsyncMock(return_value={"is_cut_labels": True})

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order
    await bot_client.send_business_photo()  # feedback
    await bot_client.send_business_photo()  # cut labels

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    last_message = fake_bot.sent_messages[-1]
    assert last_message.text == "☺ Вы прислали все фотографии, которые были нам нужны. Спасибо!"
    assert buyer.is_cut_labels is True


async def test_cashback_article_q4_input_requisites(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
    message_manager: MockMessageManager,
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)
    superbanking = await di_container.get(Superbanking)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_id": article.id,
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={"is_order": True, "price": 1500})
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={"is_feedback": True})
    openai_gateway.classify_cut_labels_screenshot = AsyncMock(return_value={"is_cut_labels": True})
    superbanking.get_bank_name_rus = Mock(return_value="Сбербанк")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order
    await bot_client.send_business_photo()  # feedback
    await bot_client.send_business_photo()  # cut labels
    await bot_client.send_business("89275554444 сбер")
    await bot_client.send_business("127 руб")

    last_message = message_manager.sent_messages[-1]
    await bot_client.click(last_message, InlineButtonTextLocator("✅ Да, верно"))

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    assert buyer.phone_number == "89275554444"
    assert buyer.bank == "Сбербанк"
    assert buyer.amount == 1500
