"""Backup controls and verification status for the whole statement database."""

import streamlit as st

from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.services.backups import BackupError, create_backup, latest_backup


def render_backup_panel(settings: StatementSettings) -> None:
    st.subheader("Database backups")
    st.caption(f"Backup folder: {settings.backup_dir.expanduser().resolve()}")
    st.caption(
        "Backups include the entire statement database. Required backups run before changes; "
        "nothing is deleted automatically."
    )
    if st.button("Back up now", key="backup-now"):
        try:
            with st.spinner("Creating and verifying backup…"):
                record = create_backup(settings.database_url, settings.backup_dir)
            st.success(f"Backup created and verified: {record.filename}")
        except BackupError as error:
            st.error(str(error))
    try:
        status = latest_backup(settings.database_url, settings.backup_dir)
        if status is None:
            st.info("No verified backup is recorded for this database yet.")
        else:
            st.write(f"Last successful backup (UTC): {status.record.created_at}")
            st.caption(f"File: {status.record.filename}")
            st.caption(f"Retain through: {status.record.retain_through}")
            if status.verified:
                st.caption(
                    "Verification passed: integrity checked at creation; checksum matches now."
                )
            else:
                st.error("The last backup is missing or has changed. Create a new backup.")
    except BackupError as error:
        st.error(str(error))
