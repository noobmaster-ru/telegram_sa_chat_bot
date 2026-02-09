import logging

from aiogram import Bot

from axiomai.application.exceptions.cabinet import CabinetNotFoundError
from axiomai.application.exceptions.cashback_table import CashbackTableNotFoundError
from axiomai.application.exceptions.payment import PaymentAlreadyProcessedError, PaymentNotFoundError
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.database.gateways.payment import PaymentGateway
from axiomai.infrastructure.database.gateways.user import UserGateway
from axiomai.infrastructure.database.models.payment import PaymentStatus
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.keyboards.reply import get_kb_menu

logger = logging.getLogger(__name__)


class ConfirmRefillBalancePayment:
    def __init__(
        self,
        tm: TransactionManager,
        payment_gateway: PaymentGateway,
        cabinet_gateway: CabinetGateway,
        cashback_table_gateway: CashbackTableGateway,
        user_gateway: UserGateway,
        bot: Bot,
    ) -> None:
        self._tm = tm
        self._payment_gateway = payment_gateway
        self._cabinet_gateway = cabinet_gateway
        self._cashback_table_gateway = cashback_table_gateway
        self._user_gateway = user_gateway
        self._bot = bot

    async def execute(self, admin_telegram_id: int, payment_id: int) -> None:
        payment = await self._payment_gateway.get_payment_by_id(payment_id)
        if not payment:
            raise PaymentNotFoundError(f"Payment with id {payment_id} not found")

        cashback_table = await self._cashback_table_gateway.get_cashback_table_by_id(payment.cashback_table_id)
        if not cashback_table:
            raise CashbackTableNotFoundError(
                f"Cashback_table.id = {payment.cashback_table_id} not found for the confirm payment"
            )
        cabinet = await self._cabinet_gateway.get_cabinet_by_id(cashback_table.cabinet_id)
        if not cabinet:
            raise CabinetNotFoundError(f"Cashback_table.id =  {cashback_table.cabinet_id} not found for the confirm payment")

        if payment.status != PaymentStatus.WAITING_CONFIRM:
            raise PaymentAlreadyProcessedError(
                f"Payment with id = {payment_id} has already been processed (status: {payment.status.value})"
            )

        payment.status = PaymentStatus.SUCCEEDED
        cabinet.balance += payment.amount
        cabinet.initial_balance = cabinet.balance

        await self._tm.commit()

        logger.info("refill balance payment %s confirmed by admin %s", payment_id, admin_telegram_id)

        user = await self._user_gateway.get_user_by_id(payment.user_id)
        if user and user.telegram_id:
            text = (
                f"✅ Оплата {payment_id} подтверждена.\n\n"
                f"На ваш баланс начислено {payment.amount} ₽.\n"
                "Теперь боту снова можно принимать заявки от клиентов."
            )
            await self._bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=get_kb_menu(cabinet))
