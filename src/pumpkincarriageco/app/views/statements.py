"""Read-only views of accepted statements; never imports or seeds data."""

import json
from datetime import date

import streamlit as st
from sqlalchemy.orm import Session

from pumpkincarriageco.app.statement_ui import (
    load_statement_settings,
    money_table,
    statement_database,
)
from pumpkincarriageco.ingestion.statements import category_label
from pumpkincarriageco.services.statements import (
    coverage,
    import_history,
    monthly_fee_summary,
    monthly_summary,
    source_entries,
)

st.header("Statements")
st.caption("Real financial data · Saved monthly statements · Etsy API disconnected")
st.caption("Payment means payments toward your Etsy bill; it excludes customer sales.")
settings = load_statement_settings()

with statement_database(settings) as engine, Session(engine) as session:
    history = import_history(session, settings.shop_id)
    if not history:
        st.info(
            "No statements have been imported for this shop. Use Import statements in the sidebar."
        )
    st.subheader("Import history and coverage")
    today = date.today()
    first_month = history[0].period if history else date(today.year, 1, 1)
    last_month = max(today.replace(day=1), history[-1].period) if history else today.replace(day=1)
    start = st.date_input("Coverage from", first_month, key="coverage-from")
    end = st.date_input("Coverage through", last_month, key="coverage-through")
    if isinstance(start, date) and isinstance(end, date):
        if start > end:
            st.error("Coverage end must be on or after start.")
        else:
            st.dataframe(
                coverage(session, settings.shop_id, start, end),
                hide_index=True,
                column_config={"rows": st.column_config.NumberColumn("Rows", format="%d")},
            )
            st.caption(
                "Missing months have no row count; an imported empty statement has 0 rows. "
                "The current month may be incomplete."
            )
    st.dataframe(
        [
            {
                "month": item.period.isoformat()[:7],
                "rows": item.row_count,
                "imported_at_utc": item.observed_at.isoformat(),
                "file_sha256": item.file_hash,
                "parser": item.parser_version,
                "classification": item.classification_version,
                "warnings": item.warning_count,
                "retain_through": item.retain_through.isoformat(),
            }
            for item in history
        ],
        hide_index=True,
    )
    st.subheader("Monthly statement categories")
    st.caption("All imported months. The coverage selectors above only change the coverage table.")
    st.dataframe(
        money_table(
            [
                summary | {"category": category_label(str(summary["category"]))}
                for summary in monthly_summary(session, settings.shop_id)
            ]
        ),
        hide_index=True,
    )
    st.subheader("Monthly fee breakdown")
    st.dataframe(money_table(monthly_fee_summary(session, settings.shop_id)), hide_index=True)
    st.caption(
        "Charges and credits are positive amounts. Net cost = charges − credits. "
        "Older imports remain Unclassified until the original CSVs are selected and confirmed."
    )
    if history:
        st.subheader("Source traceability")
        selected = st.selectbox(
            "Inspect imported month",
            options=[item.period for item in history],
            format_func=lambda value: value.isoformat()[:7],
        )
        st.dataframe(source_entries(session, settings.shop_id, selected), hide_index=True)
        selected_import = next(item for item in history if item.period == selected)
        st.caption(f"Accepted source file: {selected_import.source_name}")
        if selected_import.warning_count:
            st.dataframe(json.loads(selected_import.validation_json), hide_index=True)
st.caption(
    "These are statement activity totals, not revenue or profit. Taxes, bill payments, "
    "deposits, and seller costs remain separate. API reconciliation is planned for Part 3. "
    "Source dates are preserved at day precision; their timezone is not yet verified."
)
