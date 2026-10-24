"""Transactional statement acceptance; no network calls or changes to source files."""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from pumpkincarriageco.ingestion.statements import (
    CLASSIFICATION_VERSION,
    FEE_CLASSIFICATION_VERSION,
    FEE_SUBTYPES,
    PARSER_VERSION,
    Preview,
    StatementError,
    category_label,
)
from pumpkincarriageco.models import (
    DemoOrder,
    Shop,
    StatementEntry,
    StatementFeeClassification,
    StatementImport,
    StatementReference,
)


@dataclass(frozen=True)
class ImportResult:
    period: date
    status: Literal["imported", "already_imported", "classified_existing"]
    rows: int
    classified_fees: int = 0


def check_real_database(session: Session) -> None:
    if session.get(Shop, "synthetic-demo") or session.scalar(select(DemoOrder.id).limit(1)):
        raise StatementError("Real statements require a database separate from the synthetic demo")


def existing_status(session: Session, shop_id: str, preview: Preview) -> str:
    existing = session.scalar(
        select(StatementImport).where(
            StatementImport.shop_id == shop_id, StatementImport.period == preview.period
        )
    )
    if existing is None:
        return "new"
    if existing.content_hash == preview.content_hash:
        missing = session.scalar(
            select(StatementEntry.id)
            .outerjoin(
                StatementFeeClassification,
                and_(
                    StatementFeeClassification.entry_id == StatementEntry.id,
                    StatementFeeClassification.version == FEE_CLASSIFICATION_VERSION,
                ),
            )
            .where(
                StatementEntry.import_id == existing.id,
                StatementEntry.category == "fee",
                StatementFeeClassification.id.is_(None),
            )
            .limit(1)
        )
        if missing is not None:
            return "classification_available"
        return "already_imported"
    return "conflict"


def validate_previews(
    session: Session,
    shop_id: str,
    previews: list[Preview],
) -> list[str]:
    """Read-only preflight, shared with the backed-up write workflow."""
    if not shop_id.strip() or shop_id == "synthetic-demo" or len(shop_id) > 100:
        raise StatementError("A separate internal shop ID is required")
    check_real_database(session)
    if not previews:
        raise StatementError("Select at least one statement")
    if any(not preview.valid for preview in previews):
        raise StatementError("Resolve blocking validation issues before import")
    months: dict[date, str] = {}
    statuses: list[str] = []
    for preview in previews:
        if preview.period in months and months[preview.period] != preview.content_hash:
            raise StatementError("Selected files conflict for the same month")
        months[preview.period] = preview.content_hash
        status = existing_status(session, shop_id, preview)
        statuses.append(status)
        if status == "conflict":
            raise StatementError("A changed statement month requires review; nothing was replaced")
    shop = session.get(Shop, shop_id)
    if shop and shop.currency != "USD":
        raise StatementError("Selected shop currency does not match USD statements")
    return statuses


def accept_previews(
    session: Session,
    shop_id: str,
    previews: list[Preview],
) -> list[ImportResult]:
    """Persistence primitive; UI/CLI use statement_operations.import_statements for backup."""
    validate_previews(session, shop_id, previews)
    shop = session.get(Shop, shop_id)
    if shop is None:
        session.add(
            Shop(id=shop_id, name="PumpkinCarriageCo", timezone="America/New_York", currency="USD")
        )
        session.flush()
    results: list[ImportResult] = []
    for preview in previews:
        status = existing_status(session, shop_id, preview)
        if status == "classification_available":
            count = classify_existing(session, shop_id, preview)
            results.append(
                ImportResult(preview.period, "classified_existing", len(preview.rows), count)
            )
            continue
        if status == "already_imported":
            results.append(ImportResult(preview.period, "already_imported", len(preview.rows)))
            continue
        imported = StatementImport(
            shop_id=shop_id,
            period=preview.period,
            source_name=preview.source_name,
            file_hash=preview.file_hash,
            content_hash=preview.content_hash,
            parser_version=PARSER_VERSION,
            classification_version=CLASSIFICATION_VERSION,
            currency="USD",
            observed_at=datetime.now(UTC),
            retain_through=date(preview.period.year + 10, 12, 31),
            row_count=len(preview.rows),
            warning_count=len(preview.issues),
            validation_json=json.dumps(
                [{"source_row": issue.row, "code": issue.code} for issue in preview.issues]
            ),
        )
        session.add(imported)
        session.flush()
        for row in preview.rows:
            entry = StatementEntry(
                import_id=imported.id,
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
            session.add(entry)
            session.flush()
            if row.category == "fee":
                session.add(
                    StatementFeeClassification(
                        entry_id=entry.id,
                        subtype=row.fee_subtype or "unclassified",
                        version=FEE_CLASSIFICATION_VERSION,
                        observed_at=datetime.now(UTC),
                    )
                )
            session.add_all(
                [
                    StatementReference(entry_id=entry.id, kind=kind, source_id=source_id)
                    for kind, source_id in row.references
                ]
            )
        results.append(ImportResult(preview.period, "imported", len(preview.rows)))
    return results


def classify_existing(session: Session, shop_id: str, preview: Preview) -> int:
    """Annotate only hash-matched rows of an accepted equivalent source month."""
    imported = session.scalar(
        select(StatementImport).where(
            StatementImport.shop_id == shop_id, StatementImport.period == preview.period
        )
    )
    if imported is None or imported.content_hash != preview.content_hash:
        raise StatementError("Fee classification requires an unchanged accepted source")
    entries = list(
        session.scalars(
            select(StatementEntry).where(
                StatementEntry.import_id == imported.id, StatementEntry.category == "fee"
            )
        )
    )
    annotations = set(
        session.scalars(
            select(StatementFeeClassification.entry_id)
            .join(StatementEntry)
            .where(
                StatementEntry.import_id == imported.id,
                StatementFeeClassification.version == FEE_CLASSIFICATION_VERSION,
            )
        )
    )
    source_rows = {(row.fingerprint, row.occurrence): row for row in preview.rows}
    count = 0
    for entry in entries:
        if entry.id in annotations:
            continue
        row = source_rows.get((entry.fingerprint, entry.occurrence))
        if row is None or row.category != "fee":
            raise StatementError("Accepted source-row identity does not match preview")
        session.add(
            StatementFeeClassification(
                entry_id=entry.id,
                subtype=row.fee_subtype or "unclassified",
                version=FEE_CLASSIFICATION_VERSION,
                observed_at=datetime.now(UTC),
            )
        )
        count += 1
    session.flush()
    return count


def import_history(session: Session, shop_id: str) -> list[StatementImport]:
    return list(
        session.scalars(
            select(StatementImport)
            .where(StatementImport.shop_id == shop_id)
            .order_by(StatementImport.period)
        )
    )


def monthly_summary(session: Session, shop_id: str) -> list[dict[str, str | int | None]]:
    statement = (
        select(
            StatementImport.period,
            StatementEntry.category,
            func.count(StatementEntry.id),
            func.sum(StatementEntry.amount_minor),
            func.sum(StatementEntry.fees_minor),
            func.sum(StatementEntry.net_minor),
            func.sum(StatementEntry.deposit_minor),
        )
        .join(StatementEntry, StatementEntry.import_id == StatementImport.id)
        .where(StatementImport.shop_id == shop_id)
        .group_by(StatementImport.period, StatementEntry.category)
        .order_by(StatementImport.period, StatementEntry.category)
    )
    return [
        {
            "month": period.isoformat()[:7],
            "category": category,
            "rows": count,
            "amount_minor": amount,
            "fees_minor": fees,
            "net_minor": net,
            "deposit_minor": deposit,
        }
        for period, category, count, amount, fees, net, deposit in session.execute(statement)
    ]


def coverage(
    session: Session, shop_id: str, start: date, end: date
) -> list[dict[str, str | int | None]]:
    if start > end:
        raise StatementError("Coverage end must be on or after start")
    imported = {item.period: item for item in import_history(session, shop_id)}
    month = start.replace(day=1)
    result: list[dict[str, str | int | None]] = []
    while month <= end:
        item = imported.get(month)
        result.append(
            {
                "month": month.isoformat()[:7],
                "status": "imported" if item else "missing",
                "rows": item.row_count if item else None,
            }
        )
        if month.year == 9999 and month.month == 12:
            break
        month = date(month.year + (month.month == 12), month.month % 12 + 1, 1)
    return result


def source_entries(
    session: Session,
    shop_id: str,
    period: date,
) -> list[dict[str, str | int | None]]:
    entries = session.execute(
        select(StatementEntry, StatementFeeClassification.subtype)
        .join(StatementImport)
        .outerjoin(
            StatementFeeClassification,
            and_(
                StatementFeeClassification.entry_id == StatementEntry.id,
                StatementFeeClassification.version == FEE_CLASSIFICATION_VERSION,
            ),
        )
        .where(StatementImport.shop_id == shop_id, StatementImport.period == period)
        .order_by(StatementEntry.source_row)
    )
    return [
        {
            "source_row": entry.source_row,
            "activity_date": entry.activity_date.isoformat(),
            "category": category_label(entry.category),
            "fee_subtype": (
                FEE_SUBTYPES[subtype or "unclassified"] if entry.category == "fee" else None
            ),
            "amount": entry.amount_text,
            "fees": entry.fees_text,
            "net": entry.net_text,
            "deposit_minor": entry.deposit_minor,
            "source_row_sha256": entry.fingerprint,
            "occurrence": entry.occurrence,
        }
        for entry, subtype in entries
    ]


def monthly_fee_summary(session: Session, shop_id: str) -> list[dict[str, str | int]]:
    subtype = func.coalesce(StatementFeeClassification.subtype, "unclassified")
    charges = func.sum(case((StatementEntry.net_minor < 0, -StatementEntry.net_minor), else_=0))
    credits = func.sum(case((StatementEntry.net_minor > 0, StatementEntry.net_minor), else_=0))
    query = (
        select(
            StatementImport.period,
            subtype,
            func.count(StatementEntry.id),
            charges,
            credits,
        )
        .select_from(StatementEntry)
        .join(StatementImport)
        .outerjoin(
            StatementFeeClassification,
            and_(
                StatementFeeClassification.entry_id == StatementEntry.id,
                StatementFeeClassification.version == FEE_CLASSIFICATION_VERSION,
            ),
        )
        .where(
            StatementImport.shop_id == shop_id,
            StatementEntry.category == "fee",
        )
        .group_by(StatementImport.period, subtype)
        .order_by(StatementImport.period, subtype)
    )
    return [
        {
            "month": period.isoformat()[:7],
            "subtype": FEE_SUBTYPES[kind],
            "rows": count,
            "charges_minor": debit,
            "credits_minor": credit,
            "net_cost_minor": debit - credit,
        }
        for period, kind, count, debit, credit in session.execute(query)
    ]
