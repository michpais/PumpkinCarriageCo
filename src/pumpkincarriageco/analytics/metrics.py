from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class OrderAmounts(Protocol):
    @property
    def currency(self) -> str: ...
    @property
    def item_sales_minor(self) -> int: ...
    @property
    def refunds_minor(self) -> int: ...
    @property
    def shipping_income_minor(self) -> int: ...
    @property
    def fees_minor(self) -> int: ...
    @property
    def postage_minor(self) -> int: ...
    @property
    def cogs_minor(self) -> int: ...
    @property
    def units(self) -> int: ...


@dataclass(frozen=True)
class Metrics:
    orders: int
    units: int
    item_sales_minor: int
    net_revenue_minor: int
    contribution_minor: int


def summarize(orders: Iterable[OrderAmounts]) -> Metrics:
    rows = list(orders)
    if any(row.currency != "USD" for row in rows):
        raise ValueError("Demo metrics require USD; currencies cannot be combined")
    sales = sum(row.item_sales_minor for row in rows)
    revenue = sales + sum(row.shipping_income_minor - row.refunds_minor for row in rows)
    costs = sum(row.fees_minor + row.postage_minor + row.cogs_minor for row in rows)
    return Metrics(len(rows), sum(row.units for row in rows), sales, revenue, revenue - costs)


def usd(minor: int) -> str:
    return f"${Decimal(minor) / Decimal(100):,.2f}"
