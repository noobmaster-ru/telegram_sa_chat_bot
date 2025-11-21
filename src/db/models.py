# import datetime
# from sqlalchemy import (
#     Integer, String, BigInteger, TIMESTAMP, ForeignKey
# )
# from sqlalchemy.sql import func
# from sqlalchemy.orm import  Mapped, mapped_column, relationship

# from src.db.base import Base

# class UserORM(Base):
#     __tablename__ = "users"

#     id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
#     telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
#     fullname: Mapped[str | None] = mapped_column(String(64))
#     created_at: Mapped[datetime.datetime] = mapped_column(
#         TIMESTAMP(timezone=True),
#         server_default=func.now()
#     )

# # Один юзер → много кабинетов
# # У каждого кабинета есть название и ссылка на Google Sheets
# class CabinetORM(Base):
#     __tablename__ = "cabinets"

#     id: Mapped[int] = mapped_column(Integer, primary_key=True)
#     brand_name: Mapped[str] = mapped_column(String(128))  # Название кабинета
#     table_link: Mapped[str] = mapped_column(String(256))  # ссылка на таблицу
#     user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
#     created_at: Mapped[datetime.datetime] = mapped_column(
#         TIMESTAMP(timezone=True),
#         server_default=func.now()
#     )
#     deleted_at: Mapped[datetime.datetime | None] = mapped_column(TIMESTAMP(timezone=True))
#     user = relationship("UserORM", backref="cabinets")
    
    
# # Тут храним артикулы
# # В каждом артикуле есть количество и фото
# class ArticleORM(Base):
#     __tablename__ = "articles"

#     id: Mapped[int] = mapped_column(primary_key=True)
#     cabinet_id: Mapped[int] = mapped_column(ForeignKey("cabinets.id"))

#     article: Mapped[int] = mapped_column(Integer) # названия товара 
#     giveaways: Mapped[int] = mapped_column(Integer)  # количество раздач
#     photo_file_id: Mapped[str | None] = mapped_column(String(256))  # telegram file_id фото

#     created_at: Mapped[datetime.datetime] = mapped_column(
#         TIMESTAMP(timezone=True), server_default=func.now()
#     )

#     cabinet = relationship("CabinetORM", backref="articles")