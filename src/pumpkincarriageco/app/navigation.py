"""Explicit page registry for the private shop desk; no database work on navigation."""

from pathlib import Path
from typing import Literal

import streamlit as st

APP_DIR = Path(__file__).resolve().parent


def run_app(default_page: Literal["statements", "imports"] = "statements") -> None:
    st.set_page_config(
        page_title="Godmother Minnie's Shop Desk",
        page_icon="🎃",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.title("🎃 Godmother Minnie's Shop Desk")
    pages = {
        "Shop": [
            st.Page(
                APP_DIR / "views/statements.py",
                title="Statements",
                url_path="statements",
                default=default_page == "statements",
            ),
            st.Page(
                APP_DIR / "views/imports.py",
                title="Import statements",
                url_path="import-statements",
                default=default_page == "imports",
            ),
            st.Page(APP_DIR / "views/backups.py", title="Backups", url_path="backups"),
        ],
        "Examples": [
            st.Page(APP_DIR / "views/demo.py", title="Synthetic demo", url_path="synthetic-demo"),
        ],
    }
    selected = st.navigation(pages, position="sidebar")
    st.sidebar.info("Etsy disconnected. Live writes unavailable.")
    selected.run()
