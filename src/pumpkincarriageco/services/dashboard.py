from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from pumpkincarriageco.analytics.metrics import Metrics, summarize
from pumpkincarriageco.models import Shop
from pumpkincarriageco.repositories.orders import orders_in_period


@dataclass(frozen=True)
class Dashboard:
    shop_name: str
    timezone: str
    metrics: Metrics
    previous: Metrics
    observed_at: datetime | None


def load_dashboard(session: Session, shop_id: str, start: date, end: date) -> Dashboard:
    if end < start:
        raise ValueError("End date must be on or after start date")
    shop = session.get(Shop, shop_id)
    if shop is None:
        raise ValueError("Selected shop is missing; initialize the synthetic demo first")
    zone = ZoneInfo(shop.timezone)
    since = datetime.combine(start, time.min, zone).astimezone(UTC)
    until = datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC)
    previous_start = start - timedelta(days=(end - start).days + 1)
    previous_since = datetime.combine(previous_start, time.min, zone).astimezone(UTC)
    current = orders_in_period(session, shop_id, since, until)
    previous = orders_in_period(session, shop_id, previous_since, since)
    return Dashboard(
        shop.name,
        shop.timezone,
        summarize(current),
        summarize(previous),
        max((row.observed_at for row in current), default=None),
    )
