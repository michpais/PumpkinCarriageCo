"""Manual backup controls; independent of the migrated statement-table schema."""

import streamlit as st

from pumpkincarriageco.app.backup_panel import render_backup_panel
from pumpkincarriageco.app.statement_ui import load_statement_settings

st.header("Backups")
st.caption("Real financial data · Backups cover the entire statement database")
render_backup_panel(load_statement_settings())
