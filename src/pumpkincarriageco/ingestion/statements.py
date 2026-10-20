"""Strict, read-only Etsy monthly CSV parsing. Free text never leaves this adapter."""

import csv
import hashlib
import io
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

PARSER_VERSION = "etsy-monthly-v1"
CLASSIFICATION_VERSION = "statement-types-v2"
FEE_CLASSIFICATION_VERSION = "fee-titles-v1"
FEE_SUBTYPES = {
    "listing": "Listing",
    "processing": "Payment processing",
    "transaction_item": "Transaction — item",
    "transaction_shipping": "Transaction — shipping",
    "shop_setup": "Shop setup",
    "unclassified": "Unclassified",
}
MAX_FILE_BYTES = 20 * 1024 * 1024
HEADERS = (
    "Date",
    "Type",
    "Title",
    "Info",
    "Currency",
    "Amount",
    "Fees & Taxes",
    "Net",
    "Tax Details",
)
CATEGORIES = {
    "Sale": "sale",
    "Refund": "refund",
    "Fee": "fee",
    "Shipping": "shipping",
    "Tax": "tax",
    "Deposit": "deposit",
    "Payment": "funding",
    "Marketing": "marketing",
    "Buyer Fee": "buyer_fee",
}
MONEY = r"-?\$?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}"
MONTHS = {
    name: index
    for index, name in enumerate(
        (
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ),
        1,
    )
}


class StatementError(ValueError):
    """Messages contain only controlled labels and row numbers, never source values."""


@dataclass(frozen=True)
class Issue:
    row: int
    code: str
    blocking: bool = True


@dataclass(frozen=True)
class StatementRow:
    source_row: int
    fingerprint: str
    occurrence: int
    activity_date: date
    category: str
    amount_text: str
    fees_text: str
    net_text: str
    amount_minor: int | None
    fees_minor: int | None
    net_minor: int | None
    deposit_minor: int | None
    references: tuple[tuple[str, str], ...]
    fee_subtype: str | None = None


@dataclass(frozen=True)
class Preview:
    source_name: str
    period: date
    file_hash: str
    content_hash: str
    rows: tuple[StatementRow, ...] = field(repr=False)
    issues: tuple[Issue, ...]

    @property
    def valid(self) -> bool:
        return not any(issue.blocking for issue in self.issues)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def category_label(category: str) -> str:
    # Keep the legacy storage code so existing imports need no source-data rewrite.
    return "Payment" if category == "funding" else category.replace("_", " ").capitalize()


def fee_subtype(title: str) -> str:
    """Recognize statement descriptions, never infer a fee type from its amount."""
    exact = {
        "Listing fee": "listing",
        "Credit for listing fee": "listing",
        "Processing fee": "processing",
        "Credit for processing fee": "processing",
        "Transaction fee: Shipping": "transaction_shipping",
        "Credit for transaction fee on shipping": "transaction_shipping",
        "Charge added to bill for one-time shop set-up fee": "shop_setup",
    }
    if title in exact:
        return exact[title]
    for prefix in ("Transaction fee: ", "Credit for transaction fee on "):
        if title.startswith(prefix) and title[len(prefix) :].strip():
            return "transaction_item"
    return "unclassified"


def money(text: str) -> int | None:
    if text == "--":
        return None
    if not re.fullmatch(MONEY, text):
        raise StatementError("Invalid monetary format")
    value = int(Decimal(text.replace("$", "").replace(",", "")) * 100)
    if abs(value) > 10**12:
        raise StatementError("Monetary value exceeds supported range")
    return value


def activity_date(text: str) -> date:
    match = re.fullmatch(r"([A-Za-z]+) (\d{1,2}), (\d{4})", text)
    if not match or match[1] not in MONTHS:
        raise StatementError("Invalid activity date")
    try:
        return date(int(match[3]), MONTHS[match[1]], int(match[2]))
    except ValueError:
        raise StatementError("Invalid activity date") from None


def preview_path(path: Path) -> Preview:
    # Never open the source for writing; cap reads even if a file grows after stat().
    with path.open("rb") as source:
        data = source.read(MAX_FILE_BYTES + 1)
    return preview_bytes(path.name, data)


def preview_bytes(name: str, data: bytes) -> Preview:
    match = re.fullmatch(r"etsy_statement_(\d{4})_(\d{1,2})\.csv", name)
    if not match:
        raise StatementError("Expected filename etsy_statement_YYYY_M.csv")
    try:
        period = date(int(match[1]), int(match[2]), 1)
        if not 2005 <= period.year <= 9988:
            raise ValueError
    except ValueError:
        raise StatementError("Unsupported statement month") from None
    if len(data) > MAX_FILE_BYTES:
        raise StatementError("File exceeds 20 MiB limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise StatementError("Expected a UTF-8 CSV") from None
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    rows: list[StatementRow] = []
    issues: list[Issue] = []
    fingerprints: list[str] = []
    occurrences: Counter[str] = Counter()
    try:
        if tuple(next(reader, ())) != HEADERS:
            raise StatementError("CSV headers do not match the supported Etsy statement schema")
        for row_number, cells in enumerate(reader, 2):
            if len(cells) != len(HEADERS):
                issues.append(Issue(row_number, "column_count"))
                continue
            values = dict(zip(HEADERS, cells, strict=True))
            # A hash preserves identity without retaining arbitrary text or buyer/card details.
            fingerprint = digest(json.dumps(cells, ensure_ascii=True).encode())
            fingerprints.append(fingerprint)
            occurrences[fingerprint] += 1
            try:
                day = activity_date(values["Date"])
                if day.replace(day=1) != period:
                    raise StatementError("Date outside statement month")
                if values["Currency"] != "USD":
                    raise StatementError("Only USD statements are supported")
                amounts = [money(values[key]) for key in ("Amount", "Fees & Taxes", "Net")]
                amount, fees, net = amounts
            except StatementError:
                issues.append(Issue(row_number, "invalid_date_currency_or_money"))
                continue
            category = CATEGORIES.get(values["Type"], "unclassified")
            subtype = fee_subtype(values["Title"]) if category == "fee" else None
            if subtype == "unclassified":
                issues.append(Issue(row_number, "unclassified_fee", blocking=False))
            if category == "unclassified":
                issues.append(Issue(row_number, "unclassified_type", blocking=False))
            deposit = None
            if category == "deposit":
                deposit_match = re.fullmatch(
                    rf"({MONEY}) sent to your bank account", values["Title"]
                )
                if deposit_match:
                    deposit = money(deposit_match[1])
                if deposit is None or deposit <= 0 or any(v is not None for v in amounts):
                    issues.append(Issue(row_number, "unsupported_deposit"))
            elif net is None or (amount is None and fees is None):
                issues.append(Issue(row_number, "missing_activity_amount"))
            elif net != (amount or 0) + (fees or 0):
                issues.append(Issue(row_number, "net_arithmetic_mismatch"))
            if values["Tax Details"] != "--":
                issues.append(Issue(row_number, "tax_details_not_interpreted", blocking=False))
            refs: set[tuple[str, str]] = set()
            for key in ("Title", "Info"):
                for ref in re.finditer(r"\b(Order|Listing|Label) #(\d{1,30})\b", values[key]):
                    refs.add((ref[1].lower(), ref[2]))
            rows.append(
                StatementRow(
                    row_number,
                    fingerprint,
                    occurrences[fingerprint],
                    day,
                    category,
                    values["Amount"],
                    values["Fees & Taxes"],
                    values["Net"],
                    amount,
                    fees,
                    net,
                    deposit,
                    tuple(sorted(refs)),
                    subtype,
                )
            )
    except (csv.Error, OverflowError):
        raise StatementError("Malformed CSV; no rows can be imported") from None
    # Includes multiplicity, but ignores row order, BOM, and CSV quoting/newline choices.
    content_hash = digest(json.dumps(sorted(fingerprints)).encode())
    return Preview(
        name,
        period,
        digest(data),
        content_hash,
        tuple(rows),
        tuple(issues),
    )
