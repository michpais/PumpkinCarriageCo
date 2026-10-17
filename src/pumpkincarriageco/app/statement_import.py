"""Local statement preview/acceptance UI, separate from the synthetic dashboard."""

import json
from datetime import date

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pumpkincarriageco.analytics.metrics import usd
from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.ingestion.statements import Preview, StatementError, digest, preview_bytes
from pumpkincarriageco.repositories.database import make_engine
from pumpkincarriageco.services.statements import (
    accept_previews,
    check_real_database,
    coverage,
    existing_status,
    import_history,
    monthly_summary,
    source_entries,
)

st.set_page_config(page_title="Statement imports · Shop Desk", layout="wide")
st.title("Etsy monthly statements")
st.caption("Real financial data · Local access only · Etsy API disconnected")
st.info(
    "Select CSV copies for preview. Original files stay unchanged. Accepted rows are retained "
    "for 10 years after their activity year. Direct buyer details and free text are discarded."
)

try:
    settings = StatementSettings.from_env()
except ValueError:
    st.error("Invalid statement configuration. Use a local database separate from the demo.")
    st.stop()
if not settings.shop_id:
    st.error("Set PCC_STATEMENTS_SHOP_ID to a separate internal shop identifier, then restart.")
    st.stop()

uploaded = st.file_uploader("Monthly statement CSVs", type="csv", accept_multiple_files=True)
previews: list[Preview] = []
parse_failed = False
for upload in uploaded:
    try:
        previews.append(preview_bytes(upload.name, upload.getvalue()))
    except (StatementError, ValueError):
        parse_failed = True
        st.error("A selected file has an unsupported filename, encoding, size, or CSV schema.")

try:
    engine = make_engine(settings.database_url)
except (SQLAlchemyError, OSError, ValueError):
    st.error("Statement database path is unavailable. Check local storage configuration.")
    st.stop()
try:
    with Session(engine) as session:
        check_real_database(session)
        statuses = [existing_status(session, settings.shop_id, item) for item in previews]
    if previews:
        st.subheader("Review before importing")
        st.dataframe(
            [
                {
                    "month": item.period.isoformat()[:7],
                    "rows": len(item.rows),
                    "validation": "ready" if item.valid else "blocked",
                    "existing": status,
                    "warnings": sum(not issue.blocking for issue in item.issues),
                }
                for item, status in zip(previews, statuses, strict=True)
            ],
            hide_index=True,
        )
        issue_rows = [
            {
                "month": item.period.isoformat()[:7],
                "source_row": issue.row,
                "issue": issue.code,
                "blocking": issue.blocking,
            }
            for item in previews
            for issue in item.issues
        ]
        if issue_rows:
            st.dataframe(issue_rows, hide_index=True)
        preview_totals = []
        for item in previews:
            for category in sorted({row.category for row in item.rows}):
                values = [row for row in item.rows if row.category == category]
                preview_totals.append(
                    {
                        "month": item.period.isoformat()[:7],
                        "category": category,
                        "rows": len(values),
                        "statement net (USD)": (
                            usd(sum(row.net_minor or 0 for row in values))
                            if any(row.net_minor is not None for row in values)
                            else "not supplied"
                        ),
                        "deposits (USD)": (
                            usd(sum(row.deposit_minor or 0 for row in values))
                            if any(row.deposit_minor is not None for row in values)
                            else "not applicable"
                        ),
                    }
                )
        st.dataframe(preview_totals, hide_index=True)
        batch: dict[date, set[str]] = {}
        for item in previews:
            batch.setdefault(item.period, set()).add(item.content_hash)
        conflict = "conflict" in statuses or any(len(hashes) > 1 for hashes in batch.values())
        if conflict:
            st.error(
                "Changed statements for the same month require review. Nothing will be replaced."
            )
        key = digest(
            (
                settings.shop_id
                + settings.database_url
                + "".join(item.file_hash for item in previews)
            ).encode()
        )
        accepted = st.checkbox("I reviewed these months and validation issues", key=key)
        if st.button(
            "Import reviewed statements",
            disabled=(
                parse_failed or conflict or not accepted or any(not item.valid for item in previews)
            ),
        ):
            with Session(engine) as session, session.begin():
                results = accept_previews(session, settings.shop_id, previews)
            st.success(
                f"Imported {sum(item.status == 'imported' for item in results)} month(s); "
                f"{sum(item.status == 'already_imported' for item in results)} already imported."
            )
    st.subheader("Import history and coverage")
    today = date.today()
    start = st.date_input("Coverage from", date(today.year, 1, 1))
    end = st.date_input("Coverage through", today.replace(day=1))
    with Session(engine) as session:
        history = import_history(session, settings.shop_id)
        if isinstance(start, date) and isinstance(end, date):
            if start > end:
                st.error("Coverage end must be on or after start.")
            else:
                st.dataframe(coverage(session, settings.shop_id, start, end), hide_index=True)
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
        summaries = monthly_summary(session, settings.shop_id)
        st.dataframe(
            [
                {
                    key.removesuffix("_minor") + " (USD)" if key.endswith("_minor") else key: (
                        usd(value) if isinstance(value, int) else "not supplied"
                    )
                    if key.endswith("_minor")
                    else value
                    for key, value in summary.items()
                }
                for summary in summaries
            ],
            hide_index=True,
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
        "These are statement activity totals, not revenue or profit. Taxes, funding payments, "
        "deposits, and seller costs remain separate. API reconciliation is planned for Part 3. "
        "Source dates are preserved at day precision; their timezone is not yet verified."
    )
except (SQLAlchemyError, StatementError):
    st.error(
        "Statement database unavailable, demo data detected, or import conflict. "
        "Check setup and preview. No source files were changed."
    )
    st.code("uv run python -m pumpkincarriageco.services.statement_cli init")
finally:
    engine.dispose()
