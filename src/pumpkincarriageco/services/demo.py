"""Explicit synthetic fixture installation, never called by Streamlit."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from pumpkincarriageco.config import Settings
from pumpkincarriageco.models import DemoOrder, Shop
from pumpkincarriageco.repositories.database import make_engine

DEMO_SHOP_ID = "synthetic-demo"


def seed_demo(session: Session) -> None:
    shops = list(session.scalars(select(Shop)))
    if any(shop.id != DEMO_SHOP_ID for shop in shops):
        raise ValueError("Demo seeding requires an isolated demo database")
    if not shops:
        session.add(
            Shop(
                id=DEMO_SHOP_ID,
                name="Godmother Minnie · Demo",
                timezone="America/New_York",
                currency="USD",
            )
        )
        session.flush()
    existing = {row.source_id: row for row in session.scalars(select(DemoOrder))}
    expected = []
    for index, (day, sales, units) in enumerate(
        [(3, 3200, 1), (9, 6400, 2), (17, 3600, 1), (25, 7200, 2)], start=1
    ):
        expected.append(
            DemoOrder(
                shop_id=DEMO_SHOP_ID,
                source_id=f"demo-order-{index}",
                source="synthetic",
                observed_at=datetime(2026, 10, 1, tzinfo=UTC),
                ordered_at=datetime(2026, 9, day, 16, tzinfo=UTC),
                currency="USD",
                units=units,
                item_sales_minor=sales,
                refunds_minor=0,
                shipping_income_minor=500,
                fees_minor=400,
                postage_minor=450,
                cogs_minor=900 * units,
            )
        )
    if existing:
        fields = [column.name for column in DemoOrder.__table__.columns if column.name != "id"]
        if len(existing) != len(expected) or any(
            row.source_id not in existing
            or any(
                getattr(existing[row.source_id], field) != getattr(row, field) for field in fields
            )
            for row in expected
        ):
            raise ValueError("Unexpected demo contents; no records were overwritten")
        return
    session.add_all(expected)


def main() -> None:
    settings = Settings.from_env()
    if settings.shop_id != DEMO_SHOP_ID:
        raise ValueError("Demo seeding requires PCC_SHOP_ID=synthetic-demo")
    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session, session.begin():
            seed_demo(session)
        print("Synthetic demo ready: 4 orders, 6 units, September 2026. No Etsy connection.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
