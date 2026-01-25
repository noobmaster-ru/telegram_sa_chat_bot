import datetime

from sqlalchemy import BigInteger, String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)

    # новыми полями
    user_name: Mapped[str | None] = mapped_column(String(64))  # @username в телеге
    fullname: Mapped[str | None] = mapped_column(String(128))  # ФИО / имя
    email: Mapped[str | None] = mapped_column(String(256))  # e-mail для чеков и оплаты

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
