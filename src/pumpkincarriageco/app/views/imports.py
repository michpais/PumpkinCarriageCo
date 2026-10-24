"""Validated, explicitly confirmed statement uploads with mandatory pre-change backups."""

import streamlit as st
from sqlalchemy.orm import Session

from pumpkincarriageco.analytics.metrics import usd
from pumpkincarriageco.analytics.statement_fees import preview_fee_summary
from pumpkincarriageco.app.statement_ui import (
    load_statement_settings,
    money_table,
    statement_database,
)
from pumpkincarriageco.ingestion.statements import (
    FEE_CLASSIFICATION_VERSION,
    Preview,
    StatementError,
    category_label,
    digest,
    preview_bytes,
)
from pumpkincarriageco.services.statement_operations import import_statements
from pumpkincarriageco.services.statements import existing_status

st.header("Import statements")
st.caption("Real financial data · Preview and confirm · Etsy API disconnected")
st.caption("Payment means payments toward your Etsy bill; it excludes customer sales.")
st.info(
    "Select CSV copies for preview. Original files stay unchanged. Accepted rows are retained "
    "for 10 years after their activity year. Direct buyer details and free text are discarded."
)
settings = load_statement_settings()
uploaded = st.file_uploader("Monthly statement CSVs", type="csv", accept_multiple_files=True)
previews: list[Preview] = []
parse_failed = False
for upload in uploaded:
    try:
        previews.append(preview_bytes(upload.name, upload.getvalue()))
    except (StatementError, ValueError):
        parse_failed = True
        st.error("A selected file has an unsupported filename, encoding, size, or CSV schema.")

with statement_database(settings) as engine:
    with Session(engine) as session:
        statuses = [existing_status(session, settings.shop_id, item) for item in previews]
    if previews:
        st.subheader("Review before importing")
        st.dataframe(
            [
                {
                    "month": item.period.isoformat()[:7],
                    "rows": len(item.rows),
                    "validation": "ready" if item.valid else "blocked",
                    "existing": "Fee classification available"
                    if status == "classification_available"
                    else status,
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
                        "category": category_label(category),
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
        st.write("Fee breakdown preview")
        st.dataframe(
            money_table([summary for item in previews for summary in preview_fee_summary(item)]),
            hide_index=True,
        )
        if "classification_available" in statuses:
            st.info(
                "These months are already imported. Confirming adds fee classifications only; "
                "it does not add or replace financial activity."
            )
        batch: dict[str, set[str]] = {}
        for item in previews:
            batch.setdefault(item.period.isoformat(), set()).add(item.content_hash)
        conflict = "conflict" in statuses or any(len(hashes) > 1 for hashes in batch.values())
        if conflict:
            st.error(
                "Changed statements for the same month require review. Nothing will be replaced."
            )
        key = digest(
            (
                settings.shop_id
                + settings.database_url
                + FEE_CLASSIFICATION_VERSION
                + "".join(item.file_hash for item in previews)
            ).encode()
        )
        accepted = st.checkbox("I reviewed these months and validation issues", key=key)
        if st.button(
            "Import or classify reviewed statements",
            key="import-statements",
            disabled=(
                parse_failed or conflict or not accepted or any(not item.valid for item in previews)
            ),
        ):
            results = import_statements(settings, previews)
            st.success(
                f"Imported {sum(item.status == 'imported' for item in results)} month(s); "
                f"{sum(item.status == 'already_imported' for item in results)} already imported; "
                f"classified {sum(item.classified_fees for item in results)} existing fee row(s)."
            )
st.caption("View saved summaries, coverage, and source records on Statements in the sidebar.")
