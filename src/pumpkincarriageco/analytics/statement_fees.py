"""Fee charges, credits and net cost from signed statement activity, in exact cents."""

from pumpkincarriageco.ingestion.statements import FEE_SUBTYPES, Preview


def preview_fee_summary(preview: Preview) -> list[dict[str, str | int]]:
    totals: dict[str, list[int]] = {}
    for row in preview.rows:
        if row.category != "fee" or row.net_minor is None:
            continue
        subtype = row.fee_subtype or "unclassified"
        values = totals.setdefault(subtype, [0, 0, 0])
        values[0] += 1
        values[1] += max(-row.net_minor, 0)
        values[2] += max(row.net_minor, 0)
    return [
        {
            "month": preview.period.isoformat()[:7],
            "subtype": FEE_SUBTYPES[subtype],
            "rows": count,
            "charges_minor": charges,
            "credits_minor": credits,
            "net_cost_minor": charges - credits,
        }
        for subtype, (count, charges, credits) in sorted(totals.items())
    ]
