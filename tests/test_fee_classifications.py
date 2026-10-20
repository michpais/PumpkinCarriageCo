from datetime import UTC, date, datetime

import pytest
from alembic import command
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_statements import preview, source_row

from pumpkincarriageco.analytics.statement_fees import preview_fee_summary
from pumpkincarriageco.ingestion.statements import FEE_CLASSIFICATION_VERSION, fee_subtype
from pumpkincarriageco.models import (
    Shop,
    StatementEntry,
    StatementFeeClassification,
    StatementImport,
)
from pumpkincarriageco.services.statements import (
    accept_previews,
    existing_status,
    monthly_fee_summary,
    monthly_summary,
    source_entries,
)


@pytest.mark.parametrize(
    "title,expected",
    [
        ("Listing fee", "listing"),
        ("Credit for listing fee", "listing"),
        ("Processing fee", "processing"),
        ("Credit for processing fee", "processing"),
        ("Transaction fee: Synthetic mouse ears", "transaction_item"),
        ("Credit for transaction fee on Synthetic mouse ears", "transaction_item"),
        ("Transaction fee: Shipping", "transaction_shipping"),
        ("Credit for transaction fee on shipping", "transaction_shipping"),
        ("Charge added to bill for one-time shop set-up fee", "shop_setup"),
        ("Something else PRIVATE-NAME", "unclassified"),
        ("Transaction fee: ", "unclassified"),
    ],
)
def test_fee_title_rules(title, expected):
    assert fee_subtype(title) == expected


def test_fee_preview_and_report_keep_signs_and_exclude_other_categories(engine):
    parsed = preview(
        [
            source_row("Fee", "--", "-$0.20", "-$0.20", Title="Listing fee"),
            source_row("Fee", "--", "-$0.20", "-$0.20", Title="Listing fee"),
            source_row("Fee", "--", "$0.10", "$0.10", Title="Credit for listing fee"),
            source_row("Fee", "--", "$0.75", "$0.75", Title="Credit for processing fee"),
            source_row("Fee", "--", "-$0.30", "-$0.30", Title="Unknown PRIVATE-NAME"),
            source_row("Marketing", "--", "-$5.00", "-$5.00", Title="Offsite Ads"),
            source_row("Shipping", "--", "-$4.00", "-$4.00", Title="USPS shipping label"),
            source_row("Payment", "--", "$8.00", "$8.00", Title="Card Payment"),
        ]
    )
    assert [(issue.code, issue.blocking) for issue in parsed.issues] == [
        ("unclassified_fee", False)
    ]
    assert "PRIVATE-NAME" not in repr(parsed.rows)
    expected = preview_fee_summary(parsed)
    listing = next(row for row in expected if row["subtype"] == "Listing")
    assert listing == {
        "month": "2025-01",
        "subtype": "Listing",
        "rows": 3,
        "charges_minor": 40,
        "credits_minor": 10,
        "net_cost_minor": 30,
    }
    assert (
        next(row for row in expected if row["subtype"] == "Payment processing")["net_cost_minor"]
        == -75
    )
    with Session(engine) as session, session.begin():
        accept_previews(session, "shop-a", [parsed])
        assert monthly_fee_summary(session, "shop-a") == expected
        assert monthly_fee_summary(session, "other-shop") == []
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 8
        assert session.scalar(select(func.count()).select_from(StatementFeeClassification)) == 5
        rows = source_entries(session, "shop-a", date(2025, 1, 1))
        assert rows[0]["fee_subtype"] == "Listing"
        assert rows[-1]["category"] == "Payment"
        assert rows[-1]["fee_subtype"] is None
        # A prior classification version must not duplicate or change current report amounts.
        first = session.scalar(select(StatementEntry.id).order_by(StatementEntry.id))
        session.add(
            StatementFeeClassification(
                entry_id=first,
                subtype="processing",
                version="older-test-version",
                observed_at=datetime.now(UTC),
            )
        )
        session.flush()
        assert monthly_fee_summary(session, "shop-a") == expected


def snapshot(engine):
    with engine.connect() as connection:
        return [
            list(connection.execute(select(table)).all())
            for table in (
                StatementImport.__table__,
                StatementEntry.__table__,
            )
        ]


def test_upgrade_and_confirmed_reclassification_preserve_legacy_source(engine, migration_config):
    # Simulate a genuine v0002 database, whose importer never saved fee descriptions.
    command.downgrade(migration_config, "0002")
    rows = [
        source_row("Fee", "--", "-$0.20", "-$0.20", Title="Listing fee"),
        source_row("Fee", "--", "-$0.20", "-$0.20", Title="Listing fee"),
        source_row("Fee", "--", "$0.10", "$0.10", Title="Credit for listing fee"),
    ]
    parsed = preview(rows)
    with engine.begin() as connection:
        connection.execute(
            Shop.__table__.insert().values(id="legacy", name="Test", timezone="UTC", currency="USD")
        )
        result = connection.execute(
            StatementImport.__table__.insert().values(
                shop_id="legacy",
                period=parsed.period,
                source_name=parsed.source_name,
                file_hash=parsed.file_hash,
                content_hash=parsed.content_hash,
                parser_version="etsy-monthly-v1",
                classification_version="statement-types-v1",
                currency="USD",
                observed_at=datetime(2025, 2, 1, tzinfo=UTC),
                retain_through=date(2035, 12, 31),
                row_count=3,
                warning_count=0,
                validation_json="[]",
            )
        )
        import_id = result.inserted_primary_key[0]
        for row in parsed.rows:
            connection.execute(
                StatementEntry.__table__.insert().values(
                    import_id=import_id,
                    source_row=row.source_row,
                    fingerprint=row.fingerprint,
                    occurrence=row.occurrence,
                    activity_date=row.activity_date,
                    category=row.category,
                    amount_text=row.amount_text,
                    fees_text=row.fees_text,
                    net_text=row.net_text,
                    amount_minor=row.amount_minor,
                    fees_minor=row.fees_minor,
                    net_minor=row.net_minor,
                    deposit_minor=row.deposit_minor,
                )
            )
    before = snapshot(engine)
    command.upgrade(migration_config, "head")
    command.check(migration_config)
    assert snapshot(engine) == before
    with Session(engine) as session:
        assert existing_status(session, "legacy", parsed) == "classification_available"
        old_totals = monthly_summary(session, "legacy")
        assert monthly_fee_summary(session, "legacy")[0]["subtype"] == "Unclassified"
    # Reordering records must not move the source references or lose duplicate occurrences.
    reordered = preview(list(reversed(rows)))
    with Session(engine) as session, session.begin():
        result = accept_previews(session, "legacy", [reordered])[0]
        assert result.status == "classified_existing"
        assert result.classified_fees == 3
        assert monthly_summary(session, "legacy") == old_totals
        assert monthly_fee_summary(session, "legacy") == preview_fee_summary(parsed)
    assert snapshot(engine) == before
    with Session(engine) as session, session.begin():
        assert accept_previews(session, "legacy", [parsed])[0].status == "already_imported"
        assert session.scalar(select(func.count()).select_from(StatementFeeClassification)) == 3
        annotation = session.scalar(select(StatementFeeClassification))
        assert annotation.version == FEE_CLASSIFICATION_VERSION
        assert annotation.observed_at.tzinfo == UTC
    command.downgrade(migration_config, "0002")
    assert snapshot(engine) == before
    command.upgrade(migration_config, "head")
