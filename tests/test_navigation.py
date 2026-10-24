from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest
from test_statement_app import configure, upload
from test_statements import preview, source_row

from pumpkincarriageco.models import StatementEntry
from pumpkincarriageco.services.statements import accept_previews

MAIN = str(Path("src/pumpkincarriageco/app/main.py").resolve())


def configure_navigation(monkeypatch, database_url):
    configure(monkeypatch, database_url)
    folder = Path(make_url(database_url).database).parent
    monkeypatch.setenv("PCC_DATABASE_URL", f"sqlite:///{folder / 'separate-demo.sqlite3'}")
    return folder / "backups"


def test_main_opens_saved_statements_without_demo_or_write_controls(
    engine,
    database_url,
    monkeypatch,
):
    backup_folder = configure_navigation(monkeypatch, database_url)
    with Session(engine) as session, session.begin():
        accept_previews(session, "test-shop", [preview()])
    app = AppTest.from_file(MAIN, default_timeout=15).run()
    assert not app.exception
    assert any(header.value == "Statements" for header in app.header)
    assert not app.warning
    assert not app.metric
    assert not app.get("file_uploader")
    assert not app.button
    tables = [frame.value for frame in app.dataframe if "category" in frame.value.columns]
    assert "Sale" in tables[0]["category"].tolist()
    assert not backup_folder.exists()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 1


def test_sidebar_routes_isolate_import_and_backup_controls(engine, database_url, monkeypatch):
    backup_folder = configure_navigation(monkeypatch, database_url)
    app = AppTest.from_file(MAIN, default_timeout=15).run()
    app.switch_page("views/imports.py").run()
    assert not app.exception
    assert any(header.value == "Import statements" for header in app.header)
    assert not app.button
    app.switch_page("views/backups.py").run()
    assert not app.exception
    assert app.button(key="backup-now").label == "Back up now"
    assert not app.get("file_uploader")
    app.switch_page("views/statements.py").run()
    assert not app.exception
    assert any(header.value == "Statements" for header in app.header)
    assert not backup_folder.exists()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 0


def test_navigation_away_from_reviewed_upload_does_not_authorize_import(
    engine,
    database_url,
    monkeypatch,
):
    backup_folder = configure_navigation(monkeypatch, database_url)
    upload(monkeypatch, [source_row()])
    app = AppTest.from_file(MAIN, default_timeout=15).run()
    app.switch_page("views/imports.py").run()
    app.checkbox[0].check().run()
    assert not app.button(key="import-statements").disabled
    app.switch_page("views/backups.py").run()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 0
    assert not backup_folder.exists()
    app.switch_page("views/imports.py").run()
    assert not app.exception
    assert not app.checkbox[0].value
    assert app.button(key="import-statements").disabled
