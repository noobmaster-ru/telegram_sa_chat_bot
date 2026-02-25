import datetime

from sqlalchemy import TIMESTAMP, BigInteger, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class Buyer(Base):
    """
    Заявка покупателя на кешбек.

    Хранит информацию о покупателе, статус прохождения этапов выдачи кешбека
    и историю чата с ботом.
    """

    __tablename__ = "buyers"

    id: Mapped[int] = mapped_column(primary_key=True)

    cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id"), comment="Кабинет продавца")

    username: Mapped[str | None] = mapped_column(String(256), comment="Телеграм username (без @)")
    fullname: Mapped[str] = mapped_column(String(512), comment="Полное имя пользователя в телеграме")
    telegram_id: Mapped[int] = mapped_column(BigInteger, comment="Телеграм ID покупателя")
    nm_id: Mapped[int] = mapped_column(comment="Артикул товара")

    is_ordered: Mapped[bool] = mapped_column(default=False, comment="Скриншот заказа принят")
    is_left_feedback: Mapped[bool] = mapped_column(default=False, comment="Скриншот отзыва принят")
    is_cut_labels: Mapped[bool] = mapped_column(default=False, comment="Фото разрезанных этикеток принято")

    phone_number: Mapped[str | None] = mapped_column(String(32), comment="Номер телефона для выплаты")
    bank: Mapped[str | None] = mapped_column(String(128), comment="Название банка")
    amount: Mapped[int | None] = mapped_column(comment="Сумма кешбека в рублях")

    is_canceled: Mapped[bool] = mapped_column(default=False, comment="Заявка отменена покупателем")

    is_superbanking_paid: Mapped[bool] = mapped_column(default=False, comment="Выплата произведена через Superbanking")
    is_paid_manually: Mapped[bool] = mapped_column(default=False, comment="Выплата проставлена вручную в таблице")

    chat_history: Mapped[list[dict]] = mapped_column(JSONB, default=list, comment="История сообщений чата")

    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
