import csv
import io
from datetime import UTC, date
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.orm import Session

from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.ingestion.statements import (
    HEADERS,
    StatementError,
    money,
    preview_bytes,
    preview_path,
)
from pumpkincarriageco.models import Shop, StatementEntry, StatementImport, StatementReference
from pumpkincarriageco.services.demo import seed_demo
from pumpkincarriageco.services.statements import accept_previews, coverage, monthly_summary


def csv_bytes(rows: list[list[str]], headers=HEADERS) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def source_row(kind="Sale", amount="$10.00", fees="--", net="$10.00", **kwargs):
    values = {
        "Date": "January 2, 2025",
        "Type": kind,
        "Title": "Payment for Order #1234567890",
        "Info": "",
        "Currency": "USD",
        "Amount": amount,
        "Fees & Taxes": fees,
        "Net": net,
        "Tax Details": "--",
    }
    values.update(kwargs)
    return [values[key] for key in HEADERS]


def preview(rows=None, name="etsy_statement_2025_1.csv"):
    return preview_bytes(name, csv_bytes(rows if rows is not None else [source_row()]))


@pytest.mark.parametrize(
    "text,expected",
    [
        ("$1,234.56", 123456),
        ("-$0.29", -29),
        ("0.00", 0),
        ("--", None),
        ("$0.10", 10),
        ("$0.20", 20),
    ],
)
def test_exact_money(text, expected):
    assert money(text) == expected


@pytest.mark.parametrize("text", ["", "NaN", "$1.001", "$1e2", "1,23.45", "=1+1", "$-1.00"])
def test_reject_money_formats(text):
    with pytest.raises(StatementError):
        money(text)


def test_credits_deposits_funding_and_unknown_types():
    data = preview(
        [
            source_row(),
            source_row("Fee", "--", "-$0.45", "-$0.45"),
            source_row("Fee", "--", "$0.20", "$0.20"),
            source_row("Refund", "-$3.00", "--", "-$3.00"),
            source_row("Tax", "--", "-$0.50", "-$0.50"),
            source_row("Deposit", "--", "--", "--", Title="$6.25 sent to your bank account"),
            source_row("Payment", "--", "$2.00", "$2.00", Info="Card ending in 1111"),
            source_row("New buyer category", "--", "-$0.10", "-$0.10"),
        ]
    )
    assert data.valid
    assert data.rows[2].fees_minor == 20
    assert data.rows[5].deposit_minor == 625
    assert data.rows[5].net_minor is None
    assert data.rows[6].category == "funding"
    assert data.rows[7].category == "unclassified"
    assert [(item.code, item.blocking) for item in data.issues] == [("unclassified_type", False)]


@pytest.mark.parametrize(
    "overrides",
    [
        {"Date": "February 1, 2025"},
        {"Date": "January 32, 2025"},
        {"Currency": "EUR"},
        {"Net": "$9.99"},
        {"Amount": "--"},
        {"Net": "--"},
        {"Amount": "=HYPERLINK(secret)"},
    ],
)
def test_invalid_rows_block_import(engine: Engine, overrides):
    data = preview([source_row(**overrides)])
    assert not data.valid
    with Session(engine) as session, session.begin():
        with pytest.raises(StatementError, match="blocking"):
            accept_previews(session, "shop-a", [data])
        assert session.scalar(select(func.count()).select_from(Shop)) == 0


def test_strict_file_schema_and_row_shape():
    with pytest.raises(StatementError, match="headers"):
        preview_bytes("etsy_statement_2025_1.csv", csv_bytes([], headers=["Private"]))
    with pytest.raises(StatementError, match="filename"):
        preview_bytes("../../private.csv", b"")
    with pytest.raises(StatementError, match="UTF-8"):
        preview_bytes("etsy_statement_2025_1.csv", b"\xff")
    assert not preview_bytes("etsy_statement_2025_1.csv", csv_bytes([["too short"]])).valid
    assert not preview([source_row("Deposit", "--", "--", "--", Title="unknown")]).valid


def test_import_is_repeatable_preserves_occurrences_and_source(engine: Engine, tmp_path: Path):
    path = tmp_path / "etsy_statement_2025_1.csv"
    path.write_bytes(csv_bytes([source_row(), source_row()]))
    before = path.read_bytes()
    data = preview_path(path)
    reordered = preview_bytes("etsy_statement_2025_01.csv", before.decode("utf-8-sig").encode())
    assert reordered.file_hash != data.file_hash
    assert reordered.content_hash == data.content_hash
    with Session(engine) as session, session.begin():
        result = accept_previews(session, "shop-a", [data, reordered])
        assert [item.status for item in result] == ["imported", "already_imported"]
    with Session(engine) as session, session.begin():
        assert accept_previews(session, "shop-a", [data])[0].status == "already_imported"
        entries = list(session.scalars(select(StatementEntry).order_by(StatementEntry.source_row)))
        assert [entry.occurrence for entry in entries] == [1, 2]
        assert [entry.source_row for entry in entries] == [2, 3]
        imported = session.scalar(select(StatementImport))
        assert imported.retain_through == date(2035, 12, 31)
        assert imported.observed_at.tzinfo == UTC
        assert imported.parser_version == "etsy-monthly-v1"
        assert monthly_summary(session, "shop-a")[0]["net_minor"] == 2000
        assert monthly_summary(session, "other-shop") == []
        assert coverage(session, "shop-a", date(2025, 1, 1), date(2025, 2, 28)) == [
            {"month": "2025-01", "status": "imported", "rows": 2},
            {"month": "2025-02", "status": "missing", "rows": "unavailable"},
        ]
    assert path.read_bytes() == before


def test_conflicting_month_batch_has_no_partial_writes(engine: Engine):
    first = preview()
    changed = preview([source_row(amount="$11.00", net="$11.00")])
    february = preview([source_row(Date="February 1, 2025")], "etsy_statement_2025_2.csv")
    with Session(engine) as session, session.begin():
        accept_previews(session, "shop-a", [first])
    with pytest.raises(StatementError, match="review"):
        with Session(engine) as session, session.begin():
            accept_previews(session, "shop-a", [february, changed])
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementImport)) == 1
        assert session.scalar(select(StatementEntry.net_minor)) == 1000
    with pytest.raises(StatementError, match="conflict"):
        with Session(engine) as session, session.begin():
            accept_previews(session, "shop-b", [first, changed])
    with Session(engine) as session:
        assert session.get(Shop, "shop-b") is None


def test_row_order_dedup_and_changed_multiplicity():
    a, b = source_row(), source_row("Fee", "--", "-$0.20", "-$0.20")
    assert preview([a, b, a]).content_hash == preview([a, a, b]).content_hash
    assert preview([a, b, a]).content_hash != preview([a, b]).content_hash


def test_pii_is_discarded_before_persistence(engine: Engine):
    data = preview(
        [
            source_row(
                Title="Payment for Order #1234567890 PRIVATE-NAME alice@example.invalid",
                Info="123 Secret Street; MasterCard ending in 9999; Label #777777",
                **{"Tax Details": "Private note"},
            )
        ]
    )
    assert data.valid
    assert "PRIVATE-NAME" not in repr(data.rows)
    with Session(engine) as session, session.begin():
        accept_previews(session, "shop-a", [data])
        refs = list(session.scalars(select(StatementReference)))
        assert {(ref.kind, ref.source_id) for ref in refs} == {
            ("order", "1234567890"),
            ("label", "777777"),
        }
    with engine.connect() as connection:
        for table in (
            StatementImport.__table__,
            StatementEntry.__table__,
            StatementReference.__table__,
        ):
            stored = repr(connection.execute(select(table)).all())
            for private in ("PRIVATE-NAME", "alice@", "Secret Street", "MasterCard", "9999"):
                assert private not in stored


def test_real_and_demo_separation(engine: Engine):
    with Session(engine) as session, session.begin():
        seed_demo(session)
    with Session(engine) as session, session.begin():
        with pytest.raises(StatementError, match="separate"):
            accept_previews(session, "shop-a", [preview()])
    with Session(engine) as session, session.begin():
        with pytest.raises(StatementError, match="internal"):
            accept_previews(session, "synthetic-demo", [preview()])


def test_statement_settings_reject_demo_path(monkeypatch):
    monkeypatch.setenv("PCC_DATABASE_URL", "sqlite:///data/demo.sqlite3")
    monkeypatch.setenv("PCC_STATEMENTS_DATABASE_URL", "sqlite:///data/../data/demo.sqlite3")
    with pytest.raises(ValueError, match="separate"):
        StatementSettings.from_env()


def test_upgrade_preserves_demo_and_downgrade_only_new_tables(engine: Engine, migration_config):
    command.check(migration_config)
    with Session(engine) as session, session.begin():
        accept_previews(session, "shop-a", [preview()])
    command.downgrade(migration_config, "0001")
    tables = inspect(engine).get_table_names()
    assert "statement_imports" not in tables
    assert "demo_orders" in tables
    command.upgrade(migration_config, "head")
    command.check(migration_config)


def test_database_failure_rolls_back_entire_batch(engine: Engine, monkeypatch):
    from sqlalchemy.exc import OperationalError

    february = preview([source_row(Date="February 1, 2025")], "etsy_statement_2025_2.csv")
    with Session(engine) as session:
        real_flush = session.flush
        flushes = 0

        def fail_mid_import(*args, **kwargs):
            nonlocal flushes
            flushes += 1
            if flushes == 5:
                raise OperationalError("synthetic failure", {}, Exception("synthetic failure"))
            return real_flush(*args, **kwargs)

        monkeypatch.setattr(session, "flush", fail_mid_import)
        with pytest.raises(OperationalError), session.begin():
            accept_previews(session, "shop-a", [preview(), february])
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementImport)) == 0
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 0


def test_source_entry_access_is_shop_scoped(engine: Engine):
    from pumpkincarriageco.services.statements import source_entries

    with Session(engine) as session, session.begin():
        accept_previews(session, "shop-a", [preview()])
        assert source_entries(session, "shop-b", date(2025, 1, 1)) == []
        rows = source_entries(session, "shop-a", date(2025, 1, 1))
        assert rows[0]["source_row"] == 2
        assert rows[0]["net"] == "$10.00"


def test_cli_preview_is_read_only_and_import_requires_confirmation(tmp_path, monkeypatch, capsys):
    from pumpkincarriageco.services.statement_cli import main

    source = tmp_path / "etsy_statement_2025_1.csv"
    source.write_bytes(csv_bytes([source_row()]))
    database = tmp_path / "shop.sqlite3"
    monkeypatch.setenv("PCC_STATEMENTS_DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setattr("sys.argv", ["statement_cli", "preview", "--directory", str(tmp_path)])
    main()
    assert '"valid": true' in capsys.readouterr().out
    assert not database.exists()
    monkeypatch.setattr("sys.argv", ["statement_cli", "import", "--directory", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert "--confirm" in capsys.readouterr().err
    assert not database.exists()
