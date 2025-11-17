import datetime
from sqlalchemy import (
    Integer, String, BigInteger, TIMESTAMP, Boolean, JSON, ForeignKey
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.db.base import Base

class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(64))
    supplier_ids: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    # Связь: один пользователь может иметь несколько поставщиков
    suppliers: Mapped[list["SupplierORM"]] = relationship("SupplierORM", back_populates="user")


class SupplierORM(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supplier_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    is_active_token: Mapped[bool] = mapped_column(Boolean, default=True)

    # ForeignKey на пользователя
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    user: Mapped["UserORM"] = relationship("UserORM", back_populates="suppliers")


class WBTokenORM(Base):
    __tablename__ = "wb_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(512), unique=True)
    scopes: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expires_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class ServiceAccountORM(Base):
    __tablename__ = "service_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_account: Mapped[str] = mapped_column(String(256), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    deleted_at: Mapped[TIMESTAMP | None] = mapped_column(TIMESTAMP(timezone=True))


class TableORM(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_id: Mapped[str] = mapped_column(String(128), unique=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    expires_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    type: Mapped[str | None] = mapped_column(String(64))
    service_account_id: Mapped[int | None] = mapped_column(ForeignKey("service_accounts.id"))

    supplier: Mapped["SupplierORM"] = relationship("SupplierORM")
    service_account: Mapped["ServiceAccountORM"] = relationship("ServiceAccountORM")