"""Backup-gated application entry points for statement writes and schema upgrades."""

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session

from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.ingestion.statements import Preview, StatementError
from pumpkincarriageco.repositories.database import make_engine
from pumpkincarriageco.services.backups import BackupRecord, create_backup, database_path
from pumpkincarriageco.services.statements import ImportResult, accept_previews, validate_previews


def import_statements(settings: StatementSettings, previews: list[Preview]) -> list[ImportResult]:
    """Reserve the writer, back up the committed state, then atomically accept the batch."""
    path = database_path(settings.database_url)
    if not path.is_file():
        raise StatementError("Initialize the statement database before importing")
    engine = make_engine(settings.database_url)
    try:
        with Session(engine) as session, session.begin():
            # Backup uses another read-only connection while this reserved lock excludes writers.
            # No source data has been written when the snapshot is taken.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            statuses = validate_previews(session, settings.shop_id, previews)
            if any(status != "already_imported" for status in statuses):
                create_backup(settings.database_url, settings.backup_dir, "pre_import")
            return accept_previews(session, settings.shop_id, previews)
    finally:
        engine.dispose()


def initialize_statements(settings: StatementSettings) -> BackupRecord | None:
    """Skip backups for fresh/no-op initialization; guard every existing schema upgrade."""
    path = database_path(settings.database_url)
    existed = path.is_file() and path.stat().st_size > 0
    config = Config("alembic.ini")
    config.attributes["database_url"] = settings.database_url
    heads = set(ScriptDirectory.from_config(config).get_heads())
    engine = make_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                current = set(MigrationContext.configure(connection).get_current_heads())
                if current == heads:
                    connection.rollback()
                    return None
                has_schema = (
                    connection.exec_driver_sql(
                        "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
                    ).first()
                    is not None
                )
                backup = (
                    create_backup(settings.database_url, settings.backup_dir, "pre_migration")
                    if existed or has_schema
                    else None
                )
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
                connection.commit()
                return backup
            except BaseException:
                connection.rollback()
                raise
    finally:
        engine.dispose()
