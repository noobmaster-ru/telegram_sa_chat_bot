import datetime

from sqlalchemy import TIMESTAMP, BigInteger, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from axiomai.infrastructure.database.models.base import Base


class Cabinet(Base):
    """
    Кабинет селлера (бренд / магазин).
    Привязан к пользователю (UserORM), к бизнес-подключению и к одной или нескольким таблицам кэшбека.
    """

    __tablename__ = "cabinets"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # organization_id — внешний идентификатор организации (если понадобится привязка к WB/OZON и т.п.)
    organization_id: Mapped[int | None]
    # вместо brand_name → organization_name
    organization_name: Mapped[str] = mapped_column(String(128), comment="Название магазина/бренда на вб")

    # business_connection_id и link_code — как и раньше, для привязки бизнес-акка к кабинету
    business_connection_id: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, comment="Telegram business_connection_id для этого кабинета"
    )
    business_account_id: Mapped[int | None] = mapped_column(BigInteger(), comment="Telegram ID бизнес-аккаунта")
    link_code: Mapped[str | None] = mapped_column(
        String(64), unique=True, comment="Код для первичной привязки бизнес-аккаунта (/link_<code>)"
    )

    balance: Mapped[int] = mapped_column(default=0, comment="Текущий баланс кабинета в рублях")
    initial_balance: Mapped[int] = mapped_column(
        default=0, comment="Баланс после последнего пополнения (для расчёта порогов уведомлений)"
    )

    # 🔹 новое поле — баланс лидов
    leads_balance: Mapped[int] = mapped_column(default=0, comment="Текущий баланс лидов по кабинету")

    is_superbanking_connect: Mapped[bool] = mapped_column(
        default=False,
        comment="Включена ли выплата через Superbanking для этого кабинета",
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
