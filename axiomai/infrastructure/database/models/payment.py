import datetime
import enum
from typing import Any

from sqlalchemy import JSON, TIMESTAMP, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class ServiceType(enum.Enum):
    CASHBACK = "cashback"


class PaymentStatus(enum.Enum):
    CREATED = "created"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    WAITING_CONFIRM = "waiting_confirm"


class PaymentMethod(enum.Enum):
    KIRILL_CARD = "kirill_card"
    YOOKASSA_CARD = "yookassa_card"


class PaymentType(enum.Enum):
    REGULAR = "regular"
    ORDINAV = "ordinav"


class Payment(Base):
    """
    Платежи селлера за кэшбек-лиды.

    service_data — JSON вида:
    {
        "service": "cashback",
        "service_id": "<table_id>",
        "months": null,
        "leads": 1000,
        "discounts": [
            {
                "discount": null,
                "description": null,
                "fix_price": null
            }
        ],
        "price_per_lead": 20
    }

    Количество пополнённых лидов можно брать как сумму по payments.service_data['leads']
    по конкретной таблице (service_id == table_id).
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    # payment_id из ЮKassa
    payment_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        comment="Идентификатор платежа в ЮKassa",
    )

    service_type: Mapped[ServiceType] = mapped_column(
        SAEnum(ServiceType, name="payment_service_type"),
        default=ServiceType.CASHBACK,
    )

    # кто платил
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    email: Mapped[str | None] = mapped_column(String(256), comment="E-mail покупателя (для чеков/уведомлений)")

    # к какой таблице кэшбека относится платёж (через table_id)
    cashback_table_id: Mapped[int | None] = mapped_column(
        ForeignKey("cashback_tables.id"), comment="Если привязываем напрямую к cashback_tables"
    )

    amount: Mapped[int] = mapped_column(
        comment="Сумма платежа в базовой валюте (например, в рублях или копейках — на твой выбор)"
    )

    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.CREATED,
    )

    canceled_reason: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    payment_method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method"),
        nullable=False,
    )

    payment_type: Mapped[PaymentType] = mapped_column(
        SAEnum(PaymentType, name="payment_type"),
        nullable=False,
    )

    # RAW JSON с описанием сервиса
    service_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, comment="JSON с описанием купленного сервиса/пакета лидов"
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
