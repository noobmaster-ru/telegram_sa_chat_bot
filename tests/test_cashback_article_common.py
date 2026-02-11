import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

# Avoid importing external `openai` package during test collection.
openai_stub = types.ModuleType("axiomai.infrastructure.openai")


class _OpenAIGatewayStub:
    pass


openai_stub.OpenAIGateway = _OpenAIGatewayStub
sys.modules["axiomai.infrastructure.openai"] = openai_stub

from axiomai.infrastructure.telegram.dialogs.cashback_article import common as cashback_common


class _FakeRequestContainer:
    def __init__(self, mapping):
        self._mapping = mapping

    async def get(self, key):
        return self._mapping[key]


class _FakeDIContainer:
    def __init__(self, request_container):
        self._request_container = request_container

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._request_container

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _build_context():
    config = SimpleNamespace(delay_between_bot_messages=0)
    article = SimpleNamespace(cabinet_id=101, title="test article", instruction_text="")

    openai_gateway = Mock(spec=cashback_common.OpenAIGateway)
    openai_gateway.answer_user_question = AsyncMock(return_value={
        "response": "ok",
        "wants_to_stop": False,
        "switch_to_article_id": None,
    })

    cashback_table_gateway = Mock(spec=cashback_common.CashbackTableGateway)
    cashback_table_gateway.get_cashback_article_by_id = AsyncMock(return_value=article)
    cashback_table_gateway.get_in_stock_cashback_articles_by_cabinet_id = AsyncMock(return_value=[])

    request_container = _FakeRequestContainer({
        cashback_common.Config: config,
        cashback_common.OpenAIGateway: openai_gateway,
        cashback_common.CashbackTableGateway: cashback_table_gateway,
    })
    di_container = _FakeDIContainer(request_container)

    bot = Mock()
    bot.send_chat_action = AsyncMock()
    bot.send_message = AsyncMock()

    bg_manager = Mock()
    bg_manager.done = AsyncMock()
    bg_manager.start = AsyncMock()

    return di_container, openai_gateway, cashback_table_gateway, bot, bg_manager


async def test_process_dialog_messages_finishes_dialog_for_exact_ok_word():
    di_container, openai_gateway, cashback_table_gateway, bot, bg_manager = _build_context()
    messages = [SimpleNamespace(text=" оК ")]

    await cashback_common._process_dialog_messages(
        business_connection_id="biz_1",
        chat_id=123,
        messages=messages,
        bot=bot,
        di_container=di_container,
        step_name="check_order",
        article_id=1,
        buyer_id=None,
        bg_manager=bg_manager,
    )

    bg_manager.done.assert_not_awaited()
    openai_gateway.answer_user_question.assert_not_awaited()
    cashback_table_gateway.get_in_stock_cashback_articles_by_cabinet_id.assert_not_awaited()
    bot.send_chat_action.assert_not_awaited()
    bot.send_message.assert_not_awaited()


async def test_process_dialog_messages_does_not_finish_for_non_exact_ok_text():
    di_container, openai_gateway, cashback_table_gateway, bot, bg_manager = _build_context()
    messages = [SimpleNamespace(text="ОК, спасибо")]

    await cashback_common._process_dialog_messages(
        business_connection_id="biz_1",
        chat_id=123,
        messages=messages,
        bot=bot,
        di_container=di_container,
        step_name="check_order",
        article_id=1,
        buyer_id=None,
        bg_manager=bg_manager,
    )

    bg_manager.done.assert_not_awaited()
    openai_gateway.answer_user_question.assert_awaited_once()
    cashback_table_gateway.get_in_stock_cashback_articles_by_cabinet_id.assert_awaited_once()
    bot.send_chat_action.assert_awaited_once()
    bot.send_message.assert_awaited_once()
