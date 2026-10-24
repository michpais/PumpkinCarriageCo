"""Shared statement-page configuration, monetary display, and safe database errors."""

from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager

import streamlit as st
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from pumpkincarriageco.analytics.metrics import usd
from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.ingestion.statements import StatementError
from pumpkincarriageco.repositories.database import make_engine
from pumpkincarriageco.services.backups import BackupError
from pumpkincarriageco.services.statements import check_real_database


def load_statement_settings() -> StatementSettings:
    try:
        settings = StatementSettings.from_env()
    except ValueError:
        st.error("Invalid statement configuration. Use a local database separate from the demo.")
        st.stop()
    if not settings.shop_id:
        st.error("Set PCC_STATEMENTS_SHOP_ID to a separate internal shop identifier, then restart.")
        st.stop()
    return settings


@contextmanager
def statement_database(settings: StatementSettings) -> Iterator[Engine]:
    try:
        engine = make_engine(settings.database_url)
    except (SQLAlchemyError, OSError, ValueError):
        st.error("Statement database path is unavailable. Check local storage configuration.")
        st.stop()
    try:
        with Session(engine) as session:
            check_real_database(session)
        yield engine
    except BackupError as error:
        st.error(str(error))
        st.stop()
    except (SQLAlchemyError, StatementError):
        st.error(
            "Statement database unavailable, demo data detected, or import conflict. "
            "Check setup and preview. No source files were changed."
        )
        st.code("uv run python -m pumpkincarriageco.services.statement_cli init")
        st.stop()
    finally:
        engine.dispose()


def money_table(
    rows: Iterable[Mapping[str, str | int | None]],
) -> list[dict[str, str | int | None]]:
    return [
        {
            key.removesuffix("_minor").replace("_", " ") + " (USD)"
            if key.endswith("_minor")
            else key: (usd(value) if isinstance(value, int) else "not supplied")
            if key.endswith("_minor")
            else value
            for key, value in row.items()
        }
        for row in rows
    ]
