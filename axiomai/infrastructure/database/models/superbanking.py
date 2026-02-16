import datetime

from sqlalchemy import ARRAY, TIMESTAMP, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class SuperbankingPayout(Base):
    __tablename__ = "superbanking"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(comment="Telegram ID пользователя")
    nm_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), comment="Список артикулов товаров")
    order_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        comment="Уникальный номер перевода для идемпотентности",
    )
    phone_number: Mapped[str] = mapped_column(String(32), comment="Номер телефона для выплаты")
    bank: Mapped[str] = mapped_column(String(128), comment="Название банка")
    amount: Mapped[int] = mapped_column(comment="Сумма кешбека в рублях")
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
