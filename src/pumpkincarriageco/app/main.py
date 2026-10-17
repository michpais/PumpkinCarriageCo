from datetime import date

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pumpkincarriageco.analytics.metrics import usd
from pumpkincarriageco.config import Settings
from pumpkincarriageco.repositories.database import make_engine
from pumpkincarriageco.services.dashboard import load_dashboard

st.set_page_config(page_title="Godmother Minnie's Shop Desk", page_icon="🎃", layout="wide")
st.title("🎃 Godmother Minnie's Shop Desk")
st.caption("PumpkinCarriageCo · Phase 0 foundation")
st.warning("SYNTHETIC DEMO · These figures are invented examples, not shop performance.")
st.sidebar.header("Reporting period")
start = st.sidebar.date_input("From", date(2026, 9, 1))
end = st.sidebar.date_input("Through", date(2026, 9, 30))
st.sidebar.info("Etsy disconnected. Live writes unavailable.")

if not isinstance(start, date) or not isinstance(end, date):
    st.stop()
if end < start:
    st.error("End date must be on or after start date.")
    st.stop()

try:
    settings = Settings.from_env()
    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session:
            dashboard = load_dashboard(session, settings.shop_id, start, end)
    finally:
        engine.dispose()
except (SQLAlchemyError, ValueError):
    st.error("Demo database unavailable or configuration invalid. Follow the README setup steps.")
    st.code("uv run alembic upgrade head\nuv run python -m pumpkincarriageco.services.demo")
    st.stop()

st.subheader(dashboard.shop_name)
st.caption(f"Inclusive dates in {dashboard.timezone}; comparison uses the preceding equal days.")
current, previous = dashboard.metrics, dashboard.previous
columns = st.columns(4)
columns[0].metric("Orders", current.orders, current.orders - previous.orders)
columns[1].metric(
    "Item sales (USD)",
    usd(current.item_sales_minor),
    usd(current.item_sales_minor - previous.item_sales_minor),
)
columns[2].metric(
    "Net revenue (USD)",
    usd(current.net_revenue_minor),
    usd(current.net_revenue_minor - previous.net_revenue_minor),
)
columns[3].metric(
    "Contribution (USD)",
    usd(current.contribution_minor),
    usd(current.contribution_minor - previous.contribution_minor),
)
st.write(f"Units ordered: **{current.units}**")
if current.orders == 0:
    st.info("No synthetic orders in this period.")
st.caption(
    f"Source: synthetic fixture · Observed: {dashboard.observed_at or 'no records in period'}"
)
with st.expander("How these demo figures are calculated"):
    st.write(
        "Item sales are after discounts and exclude tax and shipping. Net revenue adds "
        "shipping income and subtracts refunds. Contribution subtracts fees, postage, "
        "and COGS. Labor and overhead are excluded; contribution is not net profit."
    )
st.info(
    "Next: approved read-only Etsy access, historical imports, and reconciliation. "
    "Views, visits, conversion, and profit are unavailable in this demo."
)
