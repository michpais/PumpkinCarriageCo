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


def upload(monkeypatch, rows):
    data = csv_bytes(rows)
    file = SimpleNamespace(name="etsy_statement_2025_1.csv", getvalue=lambda: data)
    monkeypatch.setattr("streamlit.file_uploader", lambda *args, **kwargs: [file])


def test_preview_confirmation_import_and_repeat(engine: Engine, database_url, monkeypatch):
    configure(monkeypatch, database_url)
    upload(monkeypatch, [source_row(), source_row()])
    app = AppTest.from_file(APP, default_timeout=15).run()
    assert not app.exception
    assert app.button[0].disabled
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 0
    app.checkbox[0].check().run()
    assert not app.button[0].disabled
    app.button[0].click().run()
    assert not app.exception
    assert "Imported 1 month(s)" in app.success[0].value
    assert app.selectbox[0].value.isoformat() == "2025-01-01"
    app.button[0].click().run()
    assert "1 already imported" in app.success[0].value
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 2
    upload(monkeypatch, [source_row(amount="$12.00", net="$12.00")])
    app.run()
    assert not app.exception
    assert app.button[0].disabled
    assert not app.checkbox[0].value
    assert "require review" in app.error[0].value


def test_invalid_rows_cannot_be_accepted(engine: Engine, database_url, monkeypatch):
    configure(monkeypatch, database_url)
    upload(monkeypatch, [source_row(Net="$0.01")])
    app = AppTest.from_file(APP, default_timeout=15).run()
    app.checkbox[0].check().run()
    assert app.button[0].disabled
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
