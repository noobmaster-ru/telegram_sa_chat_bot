import datetime
import enum
from typing import Any

from sqlalchemy import (
    Integer,
    String,
    BigInteger,
    TIMESTAMP,
    ForeignKey,
    Enum as SAEnum,
    JSON,
    Text,
    DateTime
)
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# from src.db.base import Base
from src.infrastructure.db.base import Base

# =====================
# USERS
# =====================

class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)

    # новыми полями
    user_name: Mapped[str | None] = mapped_column(String(64))       # @username в телеге
    fullname: Mapped[str | None] = mapped_column(String(128))       # ФИО / имя
    email: Mapped[str | None] = mapped_column(String(256))          # e-mail для чеков и оплаты

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    cabinets: Mapped[list["CabinetORM"]] = relationship(
        "CabinetORM",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    payments: Mapped[list["PaymentORM"]] = relationship(
        "PaymentORM",
        back_populates="user",
    )


# =====================
# CABINETS (кабинеты селлера)
# =====================

class CabinetORM(Base):
    """
    Кабинет селлера (бренд / магазин).
    Привязан к пользователю (UserORM), к бизнес-подключению и к одной или нескольким таблицам кэшбека.
    """

    __tablename__ = "cabinets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # organization_id — внешний идентификатор организации (если понадобится привязка к WB/OZON и т.п.)
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


    nm_id_name: Mapped[str] = mapped_column(
        String(128),
        comment="Артикул",
    )
    
    # вместо brand_name → organization_name
    organization_name: Mapped[str] = mapped_column(
        String(128),
        comment="Название магазина/бренда на вб",
    )
    # business_connection_id и link_code — как и раньше, для привязки бизнес-акка к кабинету
    business_connection_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=True,
        comment="Telegram business_connection_id для этого кабинета",
    )

    link_code: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        comment="Код для первичной привязки бизнес-аккаунта (/link_<code>)",
    )
    
    # 🔹 новое поле — баланс лидов
    leads_balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Текущий баланс лидов по кабинету",
    )
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    user: Mapped["UserORM"] = relationship(
        "UserORM",
        back_populates="cabinets",
    )

    # один кабинет → много артикулов (как и раньше)
    articles: Mapped[list["ArticleORM"]] = relationship(
        "ArticleORM",
        back_populates="cabinet",
        cascade="all, delete-orphan",
    )

    # один кабинет → одна или несколько таблиц кэшбека (в теории)
    cashback_tables: Mapped[list["CashbackTableORM"]] = relationship(
        "CashbackTableORM",
        back_populates="cabinet",
        cascade="all, delete-orphan",
    )


# =====================
# ARTICLES (артикулы)
# =====================

class ArticleORM(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id"), nullable=False)

    article: Mapped[int] = mapped_column(Integer)  # артикул товара
    nm_id_name: Mapped[str | None] = mapped_column(String(256))  # название товара
    photo_file_id: Mapped[str | None] = mapped_column(String(256))  # telegram file_id фото

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )

    cabinet: Mapped["CabinetORM"] = relationship(
        "CabinetORM",
        back_populates="articles",
    )


# =====================
# CASHBACK TABLES (таблицы Google Sheets для кэшбека)
# =====================

class CashbackTableStatus(enum.Enum):
    NEW = "new"          # только создана, ещё не оплачена
    PAID = "paid"        # есть оплаченный баланс лидов
    DISABLED = "disabled"
    EXPIRED = "expired"  # срок действия истёк


class CashbackTableORM(Base):
    """
    Таблица кэшбека в Google Sheets.

    table_id — ИД таблицы (не ссылка), единственный неизменяемый идентификатор.
    Один cabinet может иметь несколько таблиц (например, разные кампании по времени).
    """

    __tablename__ = "cashback_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    cabinet_id: Mapped[int] = mapped_column(
        ForeignKey("cabinets.id"),
        nullable=False,
        comment="Кабинет, к которому относится эта таблица кэшбека",
    )

    # table_id — то, что ты получаешь из ссылки на гугл-таблицу (ид таблицы), уникально
    table_id: Mapped[str] = mapped_column(
        String(256),
        unique=True,
        nullable=False,
        comment="Google Sheets table_id (единственный неизменяемый элемент)",
    )

    status: Mapped[CashbackTableStatus] = mapped_column(
        SAEnum(CashbackTableStatus, name="cashback_table_status"),
        nullable=False,
        default=CashbackTableStatus.NEW,
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
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="Когда истекает оплаченный период/лимит по кэшбеку (если нужно)",
    )

    cabinet: Mapped["CabinetORM"] = relationship(
        "CabinetORM",
        back_populates="cashback_tables",
    )

    payments: Mapped[list["PaymentORM"]] = relationship(
        "PaymentORM",
        back_populates="cashback_table",
    )
    
    # НОВЫЕ поля — «живая» конфигурация из Google Sheets
    article_nm_id: Mapped[int | None] = mapped_column(Integer, nullable=True)        # C2
    article_image_url: Mapped[str | None] = mapped_column(String, nullable=True)     # E2
    article_title: Mapped[str | None] = mapped_column(String, nullable=True)         # F2
    brand_name: Mapped[str | None] = mapped_column(String, nullable=True)            # G2
    instruction_text: Mapped[str | None] = mapped_column(Text, nullable=True)        # H2
    last_synced_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


# =====================
# PAYMENTS (платежи за лиды кэшбека)
# =====================

class ServiceType(enum.Enum):
    CASHBACK = "cashback"


class PaymentStatus(enum.Enum):
    CREATED = "created"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    WAITING_CONFIRM = "waiting_confirm"


class PaymentMethod(enum.Enum):
    KIRILL_CARD = "kirill_card"
    YOOKASSA_CARD = "ukassa_card"  # ukassa_card == платёж через ЮKassa


class PaymentType(enum.Enum):
    REGULAR = "regular"
    ORDINAV = "ordinav"  # оставляю твоё написание, чтобы не путаться с бизнес-логикой


class PaymentORM(Base):
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
        ]
    }

    Количество пополнённых лидов можно брать как сумму по payments.service_data['leads']
    по конкретной таблице (service_id == table_id).
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # payment_id из ЮKassa
    payment_id: Mapped[str | None] = mapped_column(
        String(128),
        unique=True,
        nullable=True,
        comment="Идентификатор платежа в ЮKassa",
    )

    service_type: Mapped[ServiceType] = mapped_column(
        SAEnum(ServiceType, name="payment_service_type"),
        nullable=False,
        default=ServiceType.CASHBACK,
    )

    # кто платил
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
        comment="E-mail покупателя (для чеков/уведомлений)",
    )

    # к какой таблице кэшбека относится платёж (через table_id)
    cashback_table_id: Mapped[int | None] = mapped_column(
        ForeignKey("cashback_tables.id"),
        nullable=True,
        comment="Если привязываем напрямую к cashback_tables",
    )

    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Сумма платежа в базовой валюте (например, в рублях или копейках — на твой выбор)",
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
        JSON,
        nullable=False,
        comment="JSON с описанием купленного сервиса/пакета лидов",
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

    user: Mapped["UserORM"] = relationship(
        "UserORM",
        back_populates="payments",
    )

    cashback_table: Mapped["CashbackTableORM"] = relationship(
        "CashbackTableORM",
        back_populates="payments",
    )