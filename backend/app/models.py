from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    screenshot_id: Mapped[str] = mapped_column(String(255))
    size: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(32))
    price_cny: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    # цена фиксируется на момент оформления
    total_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(32), index=True)
    recipient: Mapped[str] = mapped_column(Text)
    track_number: Mapped[str | None] = mapped_column(String(64))
    # чек об оплате (file_id в Telegram), пока заказ в «Ожидает оплаты»
    receipt_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(lazy="joined", innerjoin=True)
    history: Mapped[list["StatusLog"]] = relationship(order_by="StatusLog.id", lazy="selectin")


class StatusLog(Base):
    __tablename__ = "status_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    # кто сменил: client / admin_bot / admin_site
    actor: Mapped[str] = mapped_column(String(16), default="admin_bot")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
