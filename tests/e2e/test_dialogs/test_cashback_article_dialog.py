import re
from unittest.mock import AsyncMock, Mock

from aiogram_dialog.test_tools import MockMessageManager
from aiogram_dialog.test_tools.keyboard import InlineButtonTextLocator
from sqlalchemy import select

from axiomai.constants import AXIOMAI_COMMISSION, SUPERBANKING_COMMISSION
from axiomai.infrastructure.database.models import Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackTableStatus
from axiomai.infrastructure.openai import OpenAIGateway
from axiomai.infrastructure.superbanking import Superbanking
from tests.e2e.conftest import cashback_table_factory, cashback_article_factory
from tests.e2e.test_dialogs.conftest import FakeBotClient, FakeBot


async def test_exact_ok_word_silently_ignores_message(
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
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_ids": [article.id],
    })

    await bot_client.send_business("хочу кешбек")
    initial_message_count = len(fake_bot.sent_messages)

    await bot_client.send_business(" оК ")

    assert len(fake_bot.sent_messages) == initial_message_count
    openai_gateway.answer_user_question.assert_not_awaited()


async def test_non_exact_ok_text_triggers_openai_response(
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
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_ids": [article.id],
    })
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "Рад помочь!",
        "wants_to_stop": False,
        "switch_to_article_id": None,
    })

    await bot_client.send_business("хочу кешбек")
    initial_message_count = len(fake_bot.sent_messages)

    await bot_client.send_business("ОК, спасибо")

    assert len(fake_bot.sent_messages) > initial_message_count
    openai_gateway.answer_user_question.assert_awaited_once()


async def test_cashback_article_dialog_when_cabinet_not_found(bot_client: FakeBotClient, fake_bot: FakeBot, cabinet_factory):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    await cabinet_factory(business_connection_id=bot_client.business_connection_id)

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

    assert len(fake_bot.sent_messages) == 0


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
        "article_ids": [],
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
    fake_bot: FakeBot
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
        is_ordered=True,
        is_left_feedback=True,
        is_cut_labels=True,
        is_paid_manually=True,
    )
    session.add(buyer)
    await session.flush()

    openai_gateway = await di_container.get(OpenAIGateway)
    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Здравствуйте! У нас есть товары для кешбека.",
        "article_ids": [],
    })

    await bot_client.send_business("хочу кешбек")

    called_args, called_kwargs = openai_gateway.chat_with_client.call_args
    articles_arg = called_kwargs.get("articles", called_args[1] if len(called_args) > 1 else None)
    assert articles_arg is not None
    assert {article.nm_id for article in articles_arg} == {article_other.nm_id}


async def test_skip_message_when_cabinet_has_zero_leads_balance(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot
):
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id, leads_balance=0)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)

    await bot_client.send_business("хочу кешбек")

    assert len(fake_bot.sent_messages) == 0


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
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    last_message = fake_bot.sent_messages[-1]
    assert "Скриншот заказа" in last_message.text and "принят" in last_message.text
    assert buyer.is_ordered is True
    assert cabinet.leads_balance == 999
    assert len(buyer.chat_history) == 2
    assert buyer.chat_history[1]["user"] == "[Скрин заказа]"
    assert '"is_order": true' in buyer.chat_history[1]["assistant"]


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
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_id": article.nm_id,
        "cancel_reason": None,
    })

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order
    await bot_client.send_business_photo()  # feedback

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    last_message = fake_bot.sent_messages[-1]
    assert "Скриншот отзыва" in last_message.text and "принят" in last_message.text
    assert buyer.is_left_feedback is True
    assert len(buyer.chat_history) == 3
    assert buyer.chat_history[2]["user"] == "[Скрин отзыва]"
    assert '"is_feedback": true' in buyer.chat_history[2]["assistant"]


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
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_id": article.nm_id,
        "cancel_reason": None,
    })
    openai_gateway.classify_cut_labels_photo = AsyncMock(return_value={
        "is_cut_labels": True,
        "cancel_reason": None,
    })

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order
    await bot_client.send_business_photo()  # feedback
    await bot_client.send_business_photo()  # cut labels

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    last_message = fake_bot.sent_messages[-1]
    assert last_message.text == "☺ Вы прислали все фотографии, которые были нам нужны. Спасибо!"
    assert buyer.is_cut_labels is True
    assert len(buyer.chat_history) == 4
    assert buyer.chat_history[3]["user"] == "[Скрин этикеток]"
    assert '"is_cut_labels": true' in buyer.chat_history[3]["assistant"]


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
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_id": article.nm_id,
        "cancel_reason": None,
    })
    openai_gateway.classify_cut_labels_photo = AsyncMock(return_value={
        "is_cut_labels": True,
        "cancel_reason": None,
    })
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
    assert len(buyer.chat_history) == 6
    assert buyer.chat_history[4]["user"] == "89275554444 сбер"
    assert buyer.chat_history[4]["assistant"] == "null"
    assert buyer.chat_history[5]["user"] == "127 руб"
    assert buyer.chat_history[5]["assistant"] == "null"


async def test_cashback_article_switch_to_second_article_during_dialog(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """User starts dialog with one article, then requests a second article via text message."""
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    # First message classifies article1
    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_ids": [article1.id],
    })

    await bot_client.send_business("хочу кешбек")

    buyers = (await session.scalars(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))).all()
    assert len(buyers) == 1
    assert buyers[0].nm_id == article1.nm_id

    # User sends text requesting second article during dialog (switch_to_article_id)
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "Хорошо, добавляю второй артикул!",
        "wants_to_stop": False,
        "switch_to_article_id": article2.id,
    })

    await bot_client.send_business("хочу ещё второй артикул")

    buyers = (await session.scalars(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))).all()
    assert len(buyers) == 2
    nm_ids = {b.nm_id for b in buyers}
    assert nm_ids == {article1.nm_id, article2.nm_id}


async def test_two_articles_full_q1_order_screenshots(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """User has two articles and submits order screenshots for both sequentially."""
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    # First message classifies article1
    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.",
        "article_ids": [article1.id],
    })

    await bot_client.send_business("хочу кешбек")

    # User requests second article
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "Добавляю второй артикул!",
        "wants_to_stop": False,
        "switch_to_article_id": article2.id,
    })

    await bot_client.send_business("хочу ещё второй")

    # Submit order screenshot for article1
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article1.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()

    buyer1 = await session.scalar(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id, Buyer.nm_id == article1.nm_id)
    )
    assert buyer1.is_ordered is True
    assert buyer1.amount == 1500

    # Submit order screenshot for article2
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article2.nm_id,
        "price": 2000,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()

    buyer2 = await session.scalar(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id, Buyer.nm_id == article2.nm_id)
    )
    assert buyer2.is_ordered is True
    assert buyer2.amount == 2000
    assert cabinet.leads_balance == 998


async def test_two_articles_full_flow_q1_q2_q3(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """Two articles go through the full Q1→Q2→Q3 flow, verifying all steps completed."""
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    # Start dialog with article1
    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Начнём оформление.",
        "article_ids": [article1.id],
    })
    await bot_client.send_business("хочу кешбек")

    # Switch to add article2
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "Добавляю второй артикул!",
        "wants_to_stop": False,
        "switch_to_article_id": article2.id,
    })
    await bot_client.send_business("хочу ещё второй")

    # Q1: Order screenshots for both articles
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article1.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()  # order article1

    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article2.nm_id,
        "price": 2000,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()  # order article2

    # Q2: Feedback screenshots for both articles
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_id": article1.nm_id,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()  # feedback article1

    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_id": article2.nm_id,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()  # feedback article2

    # Q3: Cut labels photos for both articles
    openai_gateway.classify_cut_labels_photo = AsyncMock(return_value={
        "is_cut_labels": True,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()  # cut labels article1
    await bot_client.send_business_photo()  # cut labels article2

    # Verify both buyers completed all steps
    buyers = (await session.scalars(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id)
    )).all()
    assert len(buyers) == 2
    for buyer in buyers:
        assert buyer.is_ordered is True
        assert buyer.is_left_feedback is True
        assert buyer.is_cut_labels is True

    # Verify total amount across both articles
    total_amount = sum(b.amount for b in buyers)
    assert total_amount == 3500

    # Verify "all photos received" message was sent
    all_photos_msg = [m for m in fake_bot.sent_messages if "Вы прислали все фотографии" in m.text]
    assert len(all_photos_msg) == 1

    # Verify leads_balance decremented twice (once per article)
    assert cabinet.leads_balance == 998


async def test_switch_back_to_completed_article_while_pending_another(
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
    article_x = await cashback_article_factory(cabinet_id=cabinet.id)
    article_y = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    # Step 1: User requests article X
    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Оформляем артикул X.",
        "article_ids": [article_x.id],
    })
    await bot_client.send_business("хочу кешбек")

    buyer_x = await session.scalar(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id, Buyer.nm_id == article_x.nm_id)
    )
    assert buyer_x is not None
    assert buyer_x.is_ordered is False

    # Step 2: User sends order screenshot for X
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article_x.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()

    await session.refresh(buyer_x)
    assert buyer_x.is_ordered is True
    assert buyer_x.amount == 1500

    # Step 3: User requests switch to article Y (without sending X's feedback yet)
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "Добавляю артикул Y!",
        "wants_to_stop": False,
        "switch_to_article_id": article_y.id,
    })
    await bot_client.send_business("хочу ещё один артикул")

    buyer_y = await session.scalar(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id, Buyer.nm_id == article_y.nm_id)
    )
    assert buyer_y is not None
    assert buyer_y.is_ordered is False

    # Step 4: User requests switch back to X (without sending Y's order screenshot)
    # CreateBuyer returns existing buyer for X (already has is_ordered=True)
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "Возвращаемся к артикулу X.",
        "wants_to_stop": False,
        "switch_to_article_id": article_x.id,
    })
    await bot_client.send_business("вернись к первому артикулу")

    # Verify: still only 2 buyers exist (no duplicate for X)
    buyers = (await session.scalars(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id)
    )).all()
    assert len(buyers) == 2
    nm_ids = {b.nm_id for b in buyers}
    assert nm_ids == {article_x.nm_id, article_y.nm_id}

    # Verify: buyer X still has is_ordered=True
    await session.refresh(buyer_x)
    assert buyer_x.is_ordered is True

    # Verify: buyer Y still has is_ordered=False
    await session.refresh(buyer_y)
    assert buyer_y.is_ordered is False

    # Step 5: To proceed, user MUST send order screenshot for Y
    # System is still at check_order step because Y is pending
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article_y.nm_id,
        "price": 2000,
        "cancel_reason": None,
    })
    await bot_client.send_business_photo()

    await session.refresh(buyer_y)
    assert buyer_y.is_ordered is True
    assert buyer_y.amount == 2000

    # Now both buyers have is_ordered=True, can proceed to feedback step
    await session.refresh(buyer_x)
    await session.refresh(buyer_y)
    assert buyer_x.is_ordered is True
    assert buyer_y.is_ordered is True


async def test_chat_history_saved_on_order_screenshot_error(
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
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(side_effect=Exception("API error"))
    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    assert buyer.is_ordered is False
    assert len(buyer.chat_history) == 2
    assert buyer.chat_history[1]["user"] == "[Скрин заказа]"
    assert buyer.chat_history[1]["assistant"] == '"classify order screenshot error"'


async def test_chat_history_saved_on_feedback_screenshot_error(
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
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    openai_gateway.classify_feedback_screenshot = AsyncMock(side_effect=Exception("API error"))

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()
    await bot_client.send_business_photo()

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    assert buyer.is_ordered is True
    assert buyer.is_left_feedback is False
    assert len(buyer.chat_history) == 3
    assert buyer.chat_history[2]["user"] == "[Скрин отзыва]"
    assert buyer.chat_history[2]["assistant"] == '"classify feedback screenshot error"'


async def test_chat_history_saved_on_cut_labels_screenshot_error(
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
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_id": article.nm_id,
        "cancel_reason": None,
    })
    openai_gateway.classify_cut_labels_photo = AsyncMock(side_effect=Exception("API error"))

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()
    await bot_client.send_business_photo()
    await bot_client.send_business_photo()

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    assert buyer.is_cut_labels is False
    assert len(buyer.chat_history) == 4
    assert buyer.chat_history[3]["user"] == "[Скрин этикеток]"
    assert buyer.chat_history[3]["assistant"] == '"classify cut labels photo error"'


async def test_multiple_articles_selected_from_predialog(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
):
    """Клиент выбирает несколько артикулов сразу через predialog"""
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Оформляем оба товара.",
        "article_ids": [article1.id, article2.id],
    })

    await bot_client.send_business("хочу ролик и губку")

    buyers = (await session.scalars(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id)
    )).all()
    assert len(buyers) == 2
    nm_ids = {b.nm_id for b in buyers}
    assert nm_ids == {article1.nm_id, article2.nm_id}


async def test_cancel_single_buyer_cancels_and_closes_dialog(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
    message_manager: MockMessageManager,
):
    """Пользователь отменяет единственную заявку — buyer.is_canceled=True, диалог закрывается."""
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_ids": [article.id],
    })

    await bot_client.send_business("хочу кешбек")

    last_message = message_manager.sent_messages[-1]
    await bot_client.click(last_message, InlineButtonTextLocator(re.escape(f"❌ Отменить (арт. {article.nm_id})")))

    buyer = await session.scalar(select(Buyer).where(Buyer.telegram_id == bot_client.user.id))
    assert buyer.is_canceled is True

    cancel_confirmation = [m for m in fake_bot.sent_messages if "заявка отменена" in m.text]
    assert len(cancel_confirmation) == 1


async def test_cancel_one_of_two_buyers_dialog_stays_open(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
    message_manager: MockMessageManager,
):
    """Пользователь отменяет одну из двух заявок — отменённая is_canceled=True, диалог остаётся."""
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Оформляем оба товара.",
        "article_ids": [article1.id, article2.id],
    })

    await bot_client.send_business("хочу кешбек")

    last_message = message_manager.sent_messages[-1]
    await bot_client.click(last_message, InlineButtonTextLocator(re.escape(f"❌ Отменить (арт. {article1.nm_id})")))

    buyer1 = await session.scalar(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id, Buyer.nm_id == article1.nm_id)
    )
    buyer2 = await session.scalar(
        select(Buyer).where(Buyer.telegram_id == bot_client.user.id, Buyer.nm_id == article2.nm_id)
    )

    assert buyer1.is_canceled is True
    assert buyer2.is_canceled is False

    cancel_confirmation = [m for m in fake_bot.sent_messages if "заявка отменена" in m.text]
    assert len(cancel_confirmation) == 1


async def test_cancel_button_not_shown_for_ordered_buyer(
    cabinet_factory,
    cashback_table_factory,
    cashback_article_factory,
    di_container,
    session,
    bot_client: FakeBotClient,
    fake_bot: FakeBot,
    message_manager: MockMessageManager,
):
    """Кнопка отмены не показывается для заявки, по которой уже принят скриншот заказа."""
    fake_bot.get_business_connection = AsyncMock(user=Mock(id=bot_client.user.id))
    cabinet = await cabinet_factory(business_connection_id=bot_client.business_connection_id)
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article1 = await cashback_article_factory(cabinet_id=cabinet.id)
    article2 = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Оформляем оба товара.",
        "article_ids": [article1.id, article2.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article1.nm_id,
        "price": 1500,
        "cancel_reason": None,
    })

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # принимаем скриншот заказа article1

    # После принятия скриншота article1 — его кнопка отмены не должна отображаться
    last_message = message_manager.sent_messages[-1]
    buttons_text = str(last_message.reply_markup)
    assert f"Отменить (арт. {article1.nm_id})" not in buttons_text
    assert f"Отменить (арт. {article2.nm_id})" in buttons_text


async def test_cashback_article_q4_not_enough_balance_sends_message(
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

    total_amount = 1500
    total_charge = total_amount + SUPERBANKING_COMMISSION + AXIOMAI_COMMISSION
    cabinet = await cabinet_factory(
        business_connection_id=bot_client.business_connection_id,
        balance=total_charge - 1,
        is_superbanking_connect=True,
    )
    await cashback_table_factory(cabinet_id=cabinet.id, status=CashbackTableStatus.PAID)
    article = await cashback_article_factory(cabinet_id=cabinet.id)
    openai_gateway = await di_container.get(OpenAIGateway)
    superbanking = await di_container.get(Superbanking)

    openai_gateway.chat_with_client = AsyncMock(return_value={
        "response": "Отлично! Начнём оформление кешбека.",
        "article_ids": [article.id],
    })
    openai_gateway.classify_order_screenshot = AsyncMock(return_value={
        "is_order": True,
        "nm_id": article.nm_id,
        "price": total_amount,
        "cancel_reason": None,
    })
    openai_gateway.classify_feedback_screenshot = AsyncMock(return_value={
        "is_feedback": True,
        "nm_id": article.nm_id,
        "cancel_reason": None,
    })
    openai_gateway.classify_cut_labels_photo = AsyncMock(return_value={
        "is_cut_labels": True,
        "cancel_reason": None,
    })
    superbanking.get_bank_name_rus = Mock(return_value="Сбербанк")

    await bot_client.send_business("хочу кешбек")
    await bot_client.send_business_photo()  # order
    await bot_client.send_business_photo()  # feedback
    await bot_client.send_business_photo()  # cut labels
    await bot_client.send_business("89275554444 сбер")
    await bot_client.send_business("1500 руб")

    last_message = message_manager.sent_messages[-1]
    await bot_client.click(last_message, InlineButtonTextLocator("✅ Да, верно"))

    sent_texts = [m.text for m in fake_bot.sent_messages]
    assert "Мы свяжемся с вами позже ☺" in sent_texts
