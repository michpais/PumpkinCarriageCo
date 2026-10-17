"""Shop and synthetic order facts. All monetary amounts are integer USD cents."""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, UniqueConstraint
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


class StatementImport(Base):
    """One accepted monthly source per shop; conflicting replacements require review."""

    __tablename__ = "statement_imports"
    __table_args__ = (
        UniqueConstraint("shop_id", "period", name="uq_statement_month"),
        UniqueConstraint("shop_id", "file_hash", name="uq_statement_file"),
        CheckConstraint("currency = 'USD'", name="ck_statement_currency"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), index=True)
    period: Mapped[date] = mapped_column(Date)
    source_name: Mapped[str] = mapped_column(String(80))
    file_hash: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    parser_version: Mapped[str] = mapped_column(String(40))
    classification_version: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    retain_through: Mapped[date] = mapped_column(Date)
    row_count: Mapped[int] = mapped_column(Integer)
    warning_count: Mapped[int] = mapped_column(Integer)
    validation_json: Mapped[str] = mapped_column(String)


class StatementEntry(Base):
    """One minimized source-row occurrence, including legitimate repeated activity."""

    __tablename__ = "statement_entries"
    __table_args__ = (
        UniqueConstraint("import_id", "source_row", name="uq_statement_source_row"),
        UniqueConstraint("import_id", "fingerprint", "occurrence", name="uq_statement_occurrence"),
        CheckConstraint("source_row >= 2 AND occurrence >= 1", name="ck_statement_row"),
        CheckConstraint(
            "category IN ('sale','refund','fee','shipping','tax','deposit',"
            "'funding','marketing','buyer_fee','unclassified')",
            name="ck_statement_category",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("statement_imports.id"), index=True)
    source_row: Mapped[int] = mapped_column(Integer)
    fingerprint: Mapped[str] = mapped_column(String(64))
    occurrence: Mapped[int] = mapped_column(Integer)
    activity_date: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(30))
    amount_text: Mapped[str] = mapped_column(String(40))
    fees_text: Mapped[str] = mapped_column(String(40))
    net_text: Mapped[str] = mapped_column(String(40))
    amount_minor: Mapped[int | None] = mapped_column(Integer)
    fees_minor: Mapped[int | None] = mapped_column(Integer)
    net_minor: Mapped[int | None] = mapped_column(Integer)
    deposit_minor: Mapped[int | None] = mapped_column(Integer)


class StatementReference(Base):
    """Only recognized order/listing/label IDs, never arbitrary descriptions."""

    __tablename__ = "statement_references"
    __table_args__ = (
        UniqueConstraint("entry_id", "kind", "source_id", name="uq_statement_reference"),
        CheckConstraint("kind IN ('order','listing','label')", name="ck_statement_reference_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("statement_entries.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10))
    source_id: Mapped[str] = mapped_column(String(30))
