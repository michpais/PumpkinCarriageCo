"""Shop and synthetic order facts. All monetary amounts are integer USD cents."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """SQLite stores naive UTC; callers always supply and receive aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must be timezone-aware")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3))


class DemoOrder(Base):
    __tablename__ = "demo_orders"
    __table_args__ = (
        UniqueConstraint("shop_id", "source_id", name="uq_demo_order_source"),
        CheckConstraint("currency = 'USD'", name="ck_demo_currency"),
        CheckConstraint("source = 'synthetic'", name="ck_demo_source"),
        CheckConstraint("units > 0", name="ck_demo_units"),
        CheckConstraint(
            "item_sales_minor >= 0 AND refunds_minor >= 0 AND shipping_income_minor >= 0 "
            "AND fees_minor >= 0 AND postage_minor >= 0 AND cogs_minor >= 0",
            name="ck_demo_amounts",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), index=True)
    source_id: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(30))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ordered_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    currency: Mapped[str] = mapped_column(String(3))
    units: Mapped[int] = mapped_column(Integer)
    item_sales_minor: Mapped[int] = mapped_column(Integer)
    refunds_minor: Mapped[int] = mapped_column(Integer)
    shipping_income_minor: Mapped[int] = mapped_column(Integer)
    fees_minor: Mapped[int] = mapped_column(Integer)
    postage_minor: Mapped[int] = mapped_column(Integer)
    cogs_minor: Mapped[int] = mapped_column(Integer)
