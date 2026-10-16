from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from alembic import command
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from pumpkincarriageco.analytics.metrics import summarize, usd
from pumpkincarriageco.models import DemoOrder, Shop
from pumpkincarriageco.repositories.orders import orders_in_period
from pumpkincarriageco.services.dashboard import load_dashboard
from pumpkincarriageco.services.demo import seed_demo


def test_money_refunds_costs_and_currency():
    order = SimpleNamespace(
        currency="USD",
        item_sales_minor=10001,
        refunds_minor=2000,
        shipping_income_minor=500,
        fees_minor=1000,
        postage_minor=600,
        cogs_minor=3000,
        units=2,
    )
    result = summarize([order])
    assert result.net_revenue_minor == 8501
    assert result.contribution_minor == 3901
    assert usd(result.contribution_minor) == "$39.01"
    assert usd(-1) == "$-0.01"
    order.currency = "EUR"
    with pytest.raises(ValueError, match="currencies"):
        summarize([order])


def test_empty_metrics():
    result = summarize([])
    assert (result.orders, result.units, result.contribution_minor) == (0, 0, 0)


def test_seed_detects_changed_source_without_overwriting(engine: Engine):
    with Session(engine) as session, session.begin():
        seed_demo(session)
        first = session.scalar(select(DemoOrder).order_by(DemoOrder.id))
        first.item_sales_minor = 1
        session.flush()
        with pytest.raises(ValueError, match="Unexpected demo contents"):
            seed_demo(session)
        assert first.item_sales_minor == 1


def test_migration_and_repeatable_seed(engine: Engine, migration_config):
    command.check(migration_config)
    with Session(engine) as session, session.begin():
        seed_demo(session)
    with Session(engine) as session, session.begin():
        seed_demo(session)
        assert session.scalar(select(func.count()).select_from(DemoOrder)) == 4
        row = session.scalar(select(DemoOrder))
        assert row.observed_at.tzinfo == UTC
        result = load_dashboard(session, "synthetic-demo", date(2026, 9, 1), date(2026, 9, 30))
        assert result.metrics.orders == 4
        assert result.metrics.units == 6
        assert result.metrics.net_revenue_minor == 22400
        assert result.metrics.contribution_minor == 13600
        assert result.previous.orders == 0
    command.downgrade(migration_config, "base")
    assert "demo_orders" not in inspect(engine).get_table_names()
    command.upgrade(migration_config, "head")


def test_source_uniqueness_and_foreign_keys(engine: Engine):
    with Session(engine) as session, session.begin():
        seed_demo(session)
    with Session(engine) as session:
        row = session.scalar(select(DemoOrder))
        values = {
            col.name: getattr(row, col.name)
            for col in DemoOrder.__table__.columns
            if col.name != "id"
        }
        session.add(DemoOrder(**values))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
        values["shop_id"] = "missing"
        session.add(DemoOrder(**values))
        with pytest.raises(IntegrityError):
            session.flush()


def test_shop_scope_and_half_open_period(engine: Engine):
    with Session(engine) as session, session.begin():
        seed_demo(session)
        session.add(Shop(id="other", name="Other", timezone="UTC", currency="USD"))
        session.flush()
        first = session.scalar(select(DemoOrder).order_by(DemoOrder.id))
        values = {
            col.name: getattr(first, col.name)
            for col in DemoOrder.__table__.columns
            if col.name != "id"
        }
        values["shop_id"] = "other"
        session.add(DemoOrder(**values))
        session.flush()
        rows = orders_in_period(
            session,
            "synthetic-demo",
            datetime(2026, 9, 3, 16, tzinfo=UTC),
            datetime(2026, 9, 9, 16, tzinfo=UTC),
        )
        assert len(rows) == 1
        assert rows[0].source_id == "demo-order-1"
        with pytest.raises(ValueError, match="isolated"):
            seed_demo(session)


def test_local_dates_and_invalid_ranges(engine: Engine):
    with Session(engine) as session, session.begin():
        seed_demo(session)
        first = session.scalar(select(DemoOrder).order_by(DemoOrder.id))
        # 23:30 Eastern the previous day, not September 3 shop-local.
        first.ordered_at = datetime(2026, 9, 3, 3, 30, tzinfo=UTC)
        session.flush()
        result = load_dashboard(session, "synthetic-demo", date(2026, 9, 3), date(2026, 9, 3))
        assert result.metrics.orders == 0
        assert result.previous.orders == 1
        with pytest.raises(ValueError, match="End date"):
            load_dashboard(session, "synthetic-demo", date(2026, 9, 3), date(2026, 9, 2))
        with pytest.raises(ValueError, match="missing"):
            load_dashboard(session, "missing", date(2026, 9, 3), date(2026, 9, 3))
        first.ordered_at = datetime(2026, 9, 3)
        with pytest.raises(StatementError, match="timezone-aware"):
            session.flush()
        session.rollback()
