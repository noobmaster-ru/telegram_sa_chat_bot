import datetime

import pytest

from axiomai.application.interactors.observe_inactive_reminders import ObserveInactiveReminders


@pytest.fixture
async def observe_inactive_reminders(di_container) -> ObserveInactiveReminders:
    return await di_container.get(ObserveInactiveReminders)


def _old_timestamp() -> datetime.datetime:
    """Возвращает timestamp 49 часов назад (больше чем 48 часов неактивности)."""
    return datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=49)


async def test_sends_order_reminder(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание об отправке скриншота заказа."""
    buyer = await buyer_factory(updated_at=_old_timestamp())

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_awaited_once()
    call_args = observe_inactive_reminders._bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == buyer.telegram_id
    assert "заказа" in call_args.kwargs["text"]


async def test_sends_feedback_reminder(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание об отправке скриншота отзыва."""
    buyer = await buyer_factory(is_ordered=True, updated_at=_old_timestamp())

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_awaited_once()
    call_args = observe_inactive_reminders._bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == buyer.telegram_id
    assert "отзыва" in call_args.kwargs["text"]


async def test_sends_labels_reminder(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание об отправке фото этикеток."""
    buyer = await buyer_factory(is_ordered=True, is_left_feedback=True, updated_at=_old_timestamp())

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_awaited_once()
    call_args = observe_inactive_reminders._bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == buyer.telegram_id
    assert "этикеток" in call_args.kwargs["text"]


async def test_sends_phone_reminder(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание об отправке номера телефона."""
    buyer = await buyer_factory(
        is_ordered=True, is_left_feedback=True, is_cut_labels=True, updated_at=_old_timestamp()
    )

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_awaited_once()
    call_args = observe_inactive_reminders._bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == buyer.telegram_id
    assert "телефона" in call_args.kwargs["text"]


async def test_sends_bank_reminder(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание об отправке названия банка."""
    buyer = await buyer_factory(
        is_ordered=True,
        is_left_feedback=True,
        is_cut_labels=True,
        phone_number="+79101234567",
        updated_at=_old_timestamp(),
    )

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_awaited_once()
    call_args = observe_inactive_reminders._bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == buyer.telegram_id
    assert "банка" in call_args.kwargs["text"]


async def test_sends_requisites_confirmation_reminder(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание о подтверждении реквизитов."""
    buyer = await buyer_factory(
        is_ordered=True,
        is_left_feedback=True,
        is_cut_labels=True,
        phone_number="+79101234567",
        bank="Сбербанк",
        updated_at=_old_timestamp(),
    )

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_awaited_once()
    call_args = observe_inactive_reminders._bot.send_message.call_args
    assert call_args.kwargs["chat_id"] == buyer.telegram_id
    assert "реквизитов" in call_args.kwargs["text"]


async def test_no_reminder_for_completed_buyer(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание НЕ отправляется для завершенных заявок."""
    await buyer_factory(
        is_ordered=True,
        is_left_feedback=True,
        is_cut_labels=True,
        phone_number="+79101234567",
        bank="Сбербанк",
        amount=500,
        updated_at=_old_timestamp(),
    )

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_not_awaited()


async def test_no_reminder_for_paid_buyer(observe_inactive_reminders, buyer_factory, session) -> None:
    """Напоминание НЕ отправляется для оплаченных заявок."""
    buyer = await buyer_factory(updated_at=_old_timestamp())
    buyer.is_superbanking_paid = True
    await session.flush()

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_not_awaited()


async def test_no_reminder_for_recently_active_buyer(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание НЕ отправляется если юзер активен менее 48 часов."""
    await buyer_factory()  # updated_at = now (по умолчанию)

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_not_awaited()


async def test_no_reminder_for_buyer_without_dialog(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание НЕ отправляется если юзер не вступил в диалог."""
    await buyer_factory(chat_history=[], updated_at=_old_timestamp())

    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_not_awaited()


async def test_updates_timestamp_after_reminder(observe_inactive_reminders, buyer_factory, session) -> None:
    """После отправки напоминания обновляется updated_at."""
    old_time = _old_timestamp()
    buyer = await buyer_factory(updated_at=old_time)

    await observe_inactive_reminders.execute()

    await session.refresh(buyer)
    assert buyer.updated_at > old_time


async def test_no_duplicate_reminder_after_send(observe_inactive_reminders, buyer_factory) -> None:
    """Напоминание НЕ отправляется повторно после первой отправки."""
    await buyer_factory(updated_at=_old_timestamp())

    await observe_inactive_reminders.execute()
    observe_inactive_reminders._bot.reset_mock()
    await observe_inactive_reminders.execute()

    observe_inactive_reminders._bot.send_message.assert_not_awaited()
