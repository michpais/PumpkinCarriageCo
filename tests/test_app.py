from datetime import date
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session
from streamlit.testing.v1 import AppTest

from pumpkincarriageco.services.demo import seed_demo

APP = str(Path("src/pumpkincarriageco/app/main.py").resolve())


def test_demo_app(engine: Engine, database_url, monkeypatch):
    monkeypatch.setenv("PCC_DATABASE_URL", database_url)
    monkeypatch.setenv("PCC_SHOP_ID", "synthetic-demo")
    with Session(engine) as session, session.begin():
        seed_demo(session)
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert "SYNTHETIC DEMO" in app.warning[0].value
    assert [metric.value for metric in app.metric] == ["4", "$204.00", "$224.00", "$136.00"]
    app.sidebar.date_input[0].set_value(date(2026, 10, 1)).run()
    assert "End date" in app.error[0].value
    assert not app.exception


def test_app_uninitialized_database(database_url, monkeypatch):
    monkeypatch.setenv("PCC_DATABASE_URL", database_url)
    monkeypatch.setenv("PCC_SHOP_ID", "synthetic-demo")
    app = AppTest.from_file(APP).run()
    assert not app.exception
    assert "database unavailable" in app.error[0].value


def test_settings_reject_empty_and_hide_url(monkeypatch):
    import pytest

    from pumpkincarriageco.config import Settings

    assert "private-password" not in repr(Settings(database_url="private-password"))
    monkeypatch.setenv("PCC_SHOP_ID", " ")
    with pytest.raises(ValueError):
        Settings.from_env()
