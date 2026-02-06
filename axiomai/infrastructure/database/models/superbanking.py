import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class SuperbankingPayout(Base):
    __tablename__ = "superbanking"

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("buyers.id"), comment="Покупатель, которому делаем выплату")
    nm_id: Mapped[int] = mapped_column(comment="Артикул товара")
    phone_number: Mapped[str] = mapped_column(String(32), comment="Номер телефона для выплаты")
    bank: Mapped[str] = mapped_column(String(128), comment="Название банка")
    amount: Mapped[int] = mapped_column(comment="Сумма кешбека в рублях")
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
