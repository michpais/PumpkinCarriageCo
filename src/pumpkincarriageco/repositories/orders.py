from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from pumpkincarriageco.models import DemoOrder


def orders_in_period(
    session: Session, shop_id: str, start: datetime, end: datetime
) -> list[DemoOrder]:
    """Half-open UTC interval, always shop-scoped."""
    return list(
        session.scalars(
            select(DemoOrder)
            .where(
                DemoOrder.shop_id == shop_id,
                DemoOrder.ordered_at >= start,
                DemoOrder.ordered_at < end,
            )
            .order_by(DemoOrder.ordered_at, DemoOrder.id)
        )
    )
