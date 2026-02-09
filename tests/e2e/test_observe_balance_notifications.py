from decimal import Decimal

import pytest

from axiomai.application.interactors.observe_balance_notifications import ObserveBalanceNotifications


@pytest.fixture
async def observe_balance_notifications(di_container) -> ObserveBalanceNotifications:
    return await di_container.get(ObserveBalanceNotifications)


async def test_sends_50_percent_notification(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """Уведомление отправляется при достижении 50% баланса."""
    user = await user_factory()
    await cabinet_factory(user_id=user.id, balance=500, initial_balance=1000)

    await observe_balance_notifications.execute()

    observe_balance_notifications._bot.send_message.assert_awaited_once()
    call_args = observe_balance_notifications._bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == user.telegram_id
    assert "500 ₽" in call_args.kwargs["text"]


async def test_sends_10_percent_notification(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """Уведомление отправляется при достижении 10% баланса."""
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id, balance=100, initial_balance=1000)

    # Симулируем что 50% уведомление уже отправлено
    await observe_balance_notifications._balance_notification_gateway.create_notification(
        cabinet_id=cabinet.id, initial_balance=1000, threshold=Decimal("0.50")
    )

    await observe_balance_notifications.execute()

    observe_balance_notifications._bot.send_message.assert_awaited_once()
    call_args = observe_balance_notifications._bot.send_message.call_args
    assert "100 ₽" in call_args.kwargs["text"]


async def test_sends_1_percent_notification(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """Уведомление отправляется при достижении 1% баланса."""
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id, balance=10, initial_balance=1000)

    # Симулируем что 50% и 10% уведомления уже отправлены
    await observe_balance_notifications._balance_notification_gateway.create_notification(
        cabinet_id=cabinet.id, initial_balance=1000, threshold=Decimal("0.50")
    )
    await observe_balance_notifications._balance_notification_gateway.create_notification(
        cabinet_id=cabinet.id, initial_balance=1000, threshold=Decimal("0.10")
    )

    await observe_balance_notifications.execute()

    observe_balance_notifications._bot.send_message.assert_awaited_once()
    call_args = observe_balance_notifications._bot.send_message.call_args
    assert "10 ₽" in call_args.kwargs["text"]


async def test_does_not_send_duplicate_notification(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """Уведомление НЕ отправляется повторно."""
    user = await user_factory()
    await cabinet_factory(user_id=user.id, balance=500, initial_balance=1000)

    await observe_balance_notifications.execute()
    await observe_balance_notifications.execute()
    await observe_balance_notifications.execute()

    observe_balance_notifications._bot.send_message.assert_awaited_once()


async def test_sends_multiple_notifications_if_balance_dropped_significantly(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """Отправляет несколько уведомлений если баланс упал ниже нескольких порогов."""
    user = await user_factory()
    await cabinet_factory(user_id=user.id, balance=5, initial_balance=1000)

    await observe_balance_notifications.execute()

    assert observe_balance_notifications._bot.send_message.await_count == 3


async def test_new_refill_resets_notification_cycle(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """После нового пополнения уведомления отправляются заново."""
    user = await user_factory()
    cabinet = await cabinet_factory(user_id=user.id, balance=500, initial_balance=1000)

    # Первый цикл
    await observe_balance_notifications.execute()
    observe_balance_notifications._bot.send_message.assert_awaited_once()

    # Новое пополнение - сброс цикла
    cabinet.balance = 1000
    cabinet.initial_balance = 2000
    observe_balance_notifications._bot.reset_mock()

    cabinet.balance = 1000  # 50% от 2000
    await observe_balance_notifications.execute()

    observe_balance_notifications._bot.send_message.assert_awaited_once()
    call_args = observe_balance_notifications._bot.send_message.call_args
    assert "1000 ₽" in call_args.kwargs["text"]


async def test_no_notification_when_balance_above_threshold(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """Уведомление не отправляется если баланс выше порога."""
    user = await user_factory()
    await cabinet_factory(user_id=user.id, balance=600, initial_balance=1000)

    await observe_balance_notifications.execute()

    observe_balance_notifications._bot.send_message.assert_not_awaited()


async def test_no_notification_when_initial_balance_zero(
    user_factory, cabinet_factory, observe_balance_notifications
) -> None:
    """Уведомление не отправляется если initial_balance = 0."""
    user = await user_factory()
    await cabinet_factory(user_id=user.id, balance=100, initial_balance=0)

    await observe_balance_notifications.execute()

    observe_balance_notifications._bot.send_message.assert_not_awaited()
