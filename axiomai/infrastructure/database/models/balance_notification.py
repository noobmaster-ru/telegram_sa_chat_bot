import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class BalanceNotification(Base):
    """
    Уведомление о низком балансе кабинета.
    Хранит информацию о том, какие пороговые уведомления были отправлены
    для конкретного цикла пополнения (initial_balance).
    """

    __tablename__ = "balance_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id"), index=True)
    initial_balance: Mapped[int] = mapped_column(comment="Баланс на момент пополнения")
    threshold: Mapped[Decimal] = mapped_column(Numeric(3, 2), comment="Порог уведомления (0.50, 0.10, 0.01)")
    sent_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        comment="Время отправки уведомления",
    )
