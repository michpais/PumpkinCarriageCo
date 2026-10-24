from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest
from test_statements import csv_bytes, source_row

from pumpkincarriageco.models import StatementEntry

APP = str(Path("src/pumpkincarriageco/app/statement_import.py").resolve())


def configure(monkeypatch, database_url):
    monkeypatch.setenv("PCC_STATEMENTS_DATABASE_URL", database_url)
    monkeypatch.setenv("PCC_DATABASE_URL", "sqlite:///data/demo.sqlite3")
    monkeypatch.setenv("PCC_STATEMENTS_SHOP_ID", "test-shop")
    monkeypatch.setenv("PCC_STATEMENTS_BACKUP_DIR", str(Path(database_url[10:]).parent / "backups"))


def upload(monkeypatch, rows):
    data = csv_bytes(rows)
    file = SimpleNamespace(name="etsy_statement_2025_1.csv", getvalue=lambda: data)
    monkeypatch.setattr("streamlit.file_uploader", lambda *args, **kwargs: [file])


def test_preview_confirmation_import_and_repeat(engine: Engine, database_url, monkeypatch):
    configure(monkeypatch, database_url)
    upload(monkeypatch, [source_row(), source_row()])
    app = AppTest.from_file(APP, default_timeout=15).run()
    assert not app.exception
    assert app.button(key="import-statements").disabled
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 0
    app.checkbox[0].check().run()
    assert not app.button(key="import-statements").disabled
    app.button(key="import-statements").click().run()
    assert not app.exception
    assert "Imported 1 month(s)" in app.success[0].value
    assert app.selectbox[0].value.isoformat() == "2025-01-01"
    app.button(key="import-statements").click().run()
    assert "1 already imported" in app.success[0].value
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 2
    upload(monkeypatch, [source_row(amount="$12.00", net="$12.00")])
    app.run()
    assert not app.exception
    assert app.button(key="import-statements").disabled
    assert not app.checkbox[0].value
    assert "require review" in app.error[0].value


def test_invalid_rows_cannot_be_accepted(engine: Engine, database_url, monkeypatch):
    configure(monkeypatch, database_url)
    upload(monkeypatch, [source_row(Net="$0.01")])
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.checkbox[0].check().run()
    assert app.button(key="import-statements").disabled
    assert not app.exception
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 0


def test_uninitialized_statement_db_and_invalid_configuration(database_url, monkeypatch):
    configure(monkeypatch, database_url)
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert "database unavailable" in app.error[0].value
    monkeypatch.setenv("PCC_STATEMENTS_DATABASE_URL", "sqlite:///data/demo.sqlite3")
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert "separate from the demo" in app.error[0].value


def test_payment_label_and_fee_breakdown(engine: Engine, database_url, monkeypatch):
    configure(monkeypatch, database_url)
    upload(
        monkeypatch,
        [
            source_row("Fee", "--", "-$0.20", "-$0.20", Title="Listing fee"),
            source_row("Fee", "--", "$0.10", "$0.10", Title="Credit for listing fee"),
            source_row("Payment", "--", "$2.00", "$2.00", Title="Card Payment"),
        ],
    )
    app = AppTest.from_file(APP, default_timeout=15).run()
    assert not app.exception
    category_tables = [frame.value for frame in app.dataframe if "category" in frame.value.columns]
    assert "Payment" in category_tables[0]["category"].tolist()
    assert "funding" not in category_tables[0]["category"].tolist()
    fee_tables = [frame.value for frame in app.dataframe if "subtype" in frame.value.columns]
    assert fee_tables[0].iloc[0]["charges (USD)"] == "$0.20"
    assert fee_tables[0].iloc[0]["credits (USD)"] == "$0.10"
    assert fee_tables[0].iloc[0]["net cost (USD)"] == "$0.10"
    app.checkbox[0].check().run()
    app.button(key="import-statements").click().run()
    assert not app.exception
    fee_tables = [frame.value for frame in app.dataframe if "subtype" in frame.value.columns]
    assert fee_tables[-1].iloc[0]["subtype"] == "Listing"


def test_manual_backup_button_and_automatic_backup_status(engine, database_url, monkeypatch):
    from sqlalchemy.engine import make_url

    from pumpkincarriageco.services.backups import latest_backup

    configure(monkeypatch, database_url)
    folder = Path(make_url(database_url).database).parent / "backups"
    app = AppTest.from_file(APP, default_timeout=15).run()
    assert not folder.exists()
    app.button(key="backup-now").click().run()
    assert not app.exception
    assert "Backup created and verified" in app.success[0].value
    assert latest_backup(database_url, folder).verified
    upload(monkeypatch, [source_row()])
    app.run()
    app.checkbox[0].check().run()
    app.button(key="import-statements").click().run()
    assert not app.exception
    latest = latest_backup(database_url, folder).record
    assert latest.reason == "pre_import"
    assert any(latest.filename in caption.value for caption in app.caption)


def test_failed_backup_blocks_ui_import(engine, database_url, monkeypatch):
    from pumpkincarriageco.services import statement_operations
    from pumpkincarriageco.services.backups import BackupError

    def fail(*args, **kwargs):
        raise BackupError("Backup folder unavailable; pending change blocked")

    configure(monkeypatch, database_url)
    upload(monkeypatch, [source_row()])
    monkeypatch.setattr(statement_operations, "create_backup", fail)
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.checkbox[0].check().run()
    app.button(key="import-statements").click().run()
    assert not app.exception
    assert "Backup folder unavailable" in app.error[0].value
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 0
