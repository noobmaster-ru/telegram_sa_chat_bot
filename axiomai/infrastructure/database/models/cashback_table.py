import datetime
import enum

from sqlalchemy import TIMESTAMP
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class CashbackTableStatus(enum.Enum):
    NEW = "new"  # только создана, ещё не оплачена
    WAITING_WRITE_PERMISSION = "waiting_write_permission"  # ждём права на запись
    VERIFIED = "verified"  # сервисный аккаунт добавлен, таблица готова к работе
    PAID = "paid"  # есть оплаченный баланс лидов
    DISABLED = "disabled"
    EXPIRED = "expired"  # срок действия истёк


class CashbackTable(Base):
    """
    Таблица кэшбека в Google Sheets.

    table_id — ИД таблицы (не ссылка), единственный неизменяемый идентификатор.
    Один cabinet может иметь несколько таблиц (например, разные кампании по времени).
    """

    __tablename__ = "cashback_tables"

    id: Mapped[int] = mapped_column(primary_key=True)

    cabinet_id: Mapped[int] = mapped_column(
        ForeignKey("cabinets.id"), comment="Кабинет, к которому относится эта таблица кэшбека"
    )

    # table_id — то, что ты получаешь из ссылки на гугл-таблицу (ид таблицы), уникально
    table_id: Mapped[str] = mapped_column(
        String(256), unique=True, comment="Google Sheets table_id (единственный неизменяемый элемент)"
    )

    status: Mapped[CashbackTableStatus] = mapped_column(
        SAEnum(CashbackTableStatus, native_enum=False), default=CashbackTableStatus.NEW
    )

    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), comment="Когда истекает оплаченный период/лимит по кэшбеку (если нужно)"
    )
    last_synced_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class CashbackArticle(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id"))

    nm_id: Mapped[int]  # артикул товара
    title: Mapped[str | None] = mapped_column(String(256))  # название товара
    image_url: Mapped[str]
    brand_name: Mapped[str]
    instruction_text: Mapped[str]
    in_stock: Mapped[bool]
    is_deleted: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
