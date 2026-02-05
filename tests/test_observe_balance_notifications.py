from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from axiomai.application.interactors.observe_balance_notifications import (
    THRESHOLDS,
    ObserveBalanceNotifications,
)


@pytest.fixture
def cabinet_gateway():
    return AsyncMock()


@pytest.fixture
def user_gateway():
    return AsyncMock()


@pytest.fixture
def balance_notification_gateway():
    return AsyncMock()


@pytest.fixture
def transaction_manager():
    return AsyncMock()


@pytest.fixture
def bot():
    return AsyncMock()


@pytest.fixture
def interactor(cabinet_gateway, user_gateway, balance_notification_gateway, transaction_manager, bot):
    return ObserveBalanceNotifications(
        cabinet_gateway=cabinet_gateway,
        user_gateway=user_gateway,
        balance_notification_gateway=balance_notification_gateway,
        transaction_manager=transaction_manager,
        bot=bot,
    )


def make_cabinet(cabinet_id: int, balance: int, initial_balance: int) -> MagicMock:
    cabinet = MagicMock()
    cabinet.id = cabinet_id
    cabinet.balance = balance
    cabinet.initial_balance = initial_balance
    return cabinet


def make_user(telegram_id: int) -> MagicMock:
    user = MagicMock()
    user.telegram_id = telegram_id
    return user


class TestObserveBalanceNotifications:
    async def test_sends_50_percent_notification(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, transaction_manager, bot
    ):
        """Уведомление отправляется при достижении 50% баланса."""
        cabinet = make_cabinet(cabinet_id=1, balance=500, initial_balance=1000)
        user = make_user(telegram_id=123456)

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = user
        balance_notification_gateway.get_sent_thresholds.return_value = []

        await interactor.execute()

        bot.send_message.assert_called_once()
        call_args = bot.send_message.call_args
        assert call_args.kwargs["chat_id"] == 123456
        assert "50%" in call_args.kwargs["text"]
        assert "500 ₽" in call_args.kwargs["text"]

        balance_notification_gateway.create_notification.assert_called_once_with(
            cabinet_id=1,
            initial_balance=1000,
            threshold=Decimal("0.50"),
        )
        transaction_manager.commit.assert_called_once()

    async def test_sends_10_percent_notification(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, transaction_manager, bot
    ):
        """Уведомление отправляется при достижении 10% баланса."""
        cabinet = make_cabinet(cabinet_id=1, balance=100, initial_balance=1000)
        user = make_user(telegram_id=123456)

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = user
        balance_notification_gateway.get_sent_thresholds.return_value = [Decimal("0.50")]

        await interactor.execute()

        bot.send_message.assert_called_once()
        call_args = bot.send_message.call_args
        assert "10%" in call_args.kwargs["text"]
        assert "100 ₽" in call_args.kwargs["text"]

        balance_notification_gateway.create_notification.assert_called_once_with(
            cabinet_id=1,
            initial_balance=1000,
            threshold=Decimal("0.10"),
        )

    async def test_sends_1_percent_notification(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, transaction_manager, bot
    ):
        """Уведомление отправляется при достижении 1% баланса."""
        cabinet = make_cabinet(cabinet_id=1, balance=10, initial_balance=1000)
        user = make_user(telegram_id=123456)

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = user
        balance_notification_gateway.get_sent_thresholds.return_value = [Decimal("0.50"), Decimal("0.10")]

        await interactor.execute()

        bot.send_message.assert_called_once()
        call_args = bot.send_message.call_args
        assert "1%" in call_args.kwargs["text"]
        assert "10 ₽" in call_args.kwargs["text"]

        balance_notification_gateway.create_notification.assert_called_once_with(
            cabinet_id=1,
            initial_balance=1000,
            threshold=Decimal("0.01"),
        )

    async def test_does_not_send_duplicate_notification(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, bot
    ):
        """Уведомление НЕ отправляется повторно если уже было отправлено."""
        cabinet = make_cabinet(cabinet_id=1, balance=500, initial_balance=1000)
        user = make_user(telegram_id=123456)

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = user
        balance_notification_gateway.get_sent_thresholds.return_value = [Decimal("0.50")]

        await interactor.execute()

        bot.send_message.assert_not_called()
        balance_notification_gateway.create_notification.assert_not_called()

    async def test_sends_multiple_notifications_if_balance_dropped_significantly(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, transaction_manager, bot
    ):
        """Отправляет несколько уведомлений если баланс упал ниже нескольких порогов."""
        cabinet = make_cabinet(cabinet_id=1, balance=5, initial_balance=1000)
        user = make_user(telegram_id=123456)

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = user
        balance_notification_gateway.get_sent_thresholds.return_value = []

        await interactor.execute()

        assert bot.send_message.call_count == 3
        assert balance_notification_gateway.create_notification.call_count == 3
        assert transaction_manager.commit.call_count == 3

    async def test_skips_cabinet_without_user(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, bot
    ):
        """Пропускает кабинет если пользователь не найден."""
        cabinet = make_cabinet(cabinet_id=1, balance=500, initial_balance=1000)

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = None

        await interactor.execute()

        bot.send_message.assert_not_called()
        balance_notification_gateway.create_notification.assert_not_called()

    async def test_skips_cabinet_without_user_telegram_id(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, bot
    ):
        """Пропускает кабинет если у пользователя нет telegram_id."""
        cabinet = make_cabinet(cabinet_id=1, balance=500, initial_balance=1000)
        user = MagicMock()
        user.telegram_id = None

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = user

        await interactor.execute()

        bot.send_message.assert_not_called()

    async def test_new_refill_resets_notification_cycle(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, transaction_manager, bot
    ):
        """После нового пополнения (другой initial_balance) уведомления отправляются заново."""
        cabinet = make_cabinet(cabinet_id=1, balance=1000, initial_balance=2000)
        user = make_user(telegram_id=123456)

        cabinet_gateway.get_cabinets_with_low_balance.return_value = [cabinet]
        user_gateway.get_user_by_cabinet_id.return_value = user
        # Уведомления были отправлены для старого initial_balance=1000, но не для нового=2000
        balance_notification_gateway.get_sent_thresholds.return_value = []

        await interactor.execute()

        bot.send_message.assert_called_once()
        call_args = bot.send_message.call_args
        assert "50%" in call_args.kwargs["text"]
        assert "1000 ₽" in call_args.kwargs["text"]

    async def test_no_cabinets_with_low_balance(
        self, interactor, cabinet_gateway, user_gateway, balance_notification_gateway, bot
    ):
        """Ничего не происходит если нет кабинетов с низким балансом."""
        cabinet_gateway.get_cabinets_with_low_balance.return_value = []

        await interactor.execute()

        user_gateway.get_user_by_cabinet_id.assert_not_called()
        bot.send_message.assert_not_called()


class TestThresholds:
    def test_thresholds_are_in_correct_order(self):
        """Пороги должны быть в порядке убывания."""
        assert THRESHOLDS == [Decimal("0.50"), Decimal("0.10"), Decimal("0.01")]

    def test_thresholds_are_decimal(self):
        """Пороги должны быть Decimal для точных вычислений."""
        for threshold in THRESHOLDS:
            assert isinstance(threshold, Decimal)
