import json
import sqlite3
from contextlib import closing

import pytest
from alembic import command
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session
from test_statements import preview, source_row

from pumpkincarriageco.config import StatementSettings
from pumpkincarriageco.ingestion.statements import StatementError
from pumpkincarriageco.models import StatementEntry, StatementImport
from pumpkincarriageco.services import backups, statement_operations
from pumpkincarriageco.services.backups import BackupError, create_backup, latest_backup
from pumpkincarriageco.services.statement_operations import import_statements, initialize_statements
from pumpkincarriageco.services.statements import accept_previews


def settings(database_url, tmp_path):
    return StatementSettings(database_url, "test-shop", tmp_path / "backups")


def test_online_backup_captures_wal_and_verifies_with_open_connection(tmp_path):
    source = tmp_path / "shop #1.sqlite3"
    database_url = f"sqlite:///{source}"
    folder = tmp_path / "backups"
    with closing(sqlite3.connect(source)) as active:
        active.execute("PRAGMA journal_mode=WAL")
        active.execute("CREATE TABLE facts (amount INTEGER)")
        active.execute("INSERT INTO facts VALUES (12345)")
        active.commit()
        assert source.with_name(source.name + "-wal").exists()
        record = create_backup(database_url, folder)
        active.execute("INSERT INTO facts VALUES (678)")
        active.commit()
        with closing(sqlite3.connect(folder / record.filename)) as snapshot:
            assert snapshot.execute("SELECT amount FROM facts").fetchall() == [(12345,)]
            assert snapshot.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert latest_backup(database_url, folder).verified
    metadata = json.loads((folder / (record.filename + ".json")).read_text())
    assert metadata["reason"] == "manual"
    assert metadata["sha256"] == backups.file_hash(folder / record.filename)
    assert "amount" not in metadata


def test_unique_snapshots_and_tampering_is_reported(engine, database_url, tmp_path):
    folder = tmp_path / "backups"
    first = create_backup(database_url, folder)
    contents = (folder / first.filename).read_bytes()
    second = create_backup(database_url, folder)
    assert first.filename != second.filename
    assert (folder / first.filename).read_bytes() == contents
    assert latest_backup(database_url, folder).record == second
    with (folder / second.filename).open("ab") as stream:
        stream.write(b"tampered")
    assert not latest_backup(database_url, folder).verified
    assert latest_backup(f"sqlite:///{tmp_path / 'other.sqlite3'}", folder) is None


def test_reject_missing_source_or_git_backup_target(engine, database_url, tmp_path):
    folder = tmp_path / "backups"
    with pytest.raises(BackupError, match="No statement database"):
        create_backup(f"sqlite:///{tmp_path / 'missing.sqlite3'}", folder)
    assert not folder.exists()
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    with pytest.raises(BackupError, match="outside Git"):
        create_backup(database_url, checkout / "backups")
    assert not (checkout / "backups").exists()
    with pytest.raises(BackupError, match="separate"):
        create_backup(database_url, tmp_path)


def test_failed_verification_does_not_publish_success(engine, database_url, tmp_path, monkeypatch):
    folder = tmp_path / "backups"

    def fail(path):
        raise BackupError("Integrity check failed")

    monkeypatch.setattr(backups, "_check_snapshot", fail)
    with pytest.raises(BackupError):
        create_backup(database_url, folder)
    assert list(folder.glob("*.sqlite3.json")) == []
    assert latest_backup(database_url, folder) is None


def test_backup_rejects_database_with_broken_references(tmp_path):
    source = tmp_path / "broken.sqlite3"
    with closing(sqlite3.connect(source)) as connection:
        connection.executescript(
            "CREATE TABLE parent (id INTEGER PRIMARY KEY);"
            "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id));"
            "INSERT INTO child VALUES (999);"
        )
        connection.commit()
    folder = tmp_path / "backups"
    with pytest.raises(BackupError, match="broken references"):
        create_backup(f"sqlite:///{source}", folder)
    assert latest_backup(f"sqlite:///{source}", folder) is None


def test_required_import_backup_precedes_write_and_repeat_skips_backup(
    engine,
    database_url,
    tmp_path,
):
    config = settings(database_url, tmp_path)
    parsed = preview()
    assert import_statements(config, [parsed])[0].status == "imported"
    record = latest_backup(database_url, config.backup_dir).record
    assert record.reason == "pre_import"
    with closing(sqlite3.connect(config.backup_dir / record.filename)) as snapshot:
        assert snapshot.execute("SELECT COUNT(*) FROM statement_imports").fetchone() == (0,)
    assert import_statements(config, [parsed])[0].status == "already_imported"
    assert len(list(config.backup_dir.glob("*.json"))) == 1
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementEntry)) == 1


def test_backup_failure_blocks_import_and_releases_lock(
    engine, database_url, tmp_path, monkeypatch
):
    config = settings(database_url, tmp_path)

    def fail(*args, **kwargs):
        raise BackupError("Backup folder unavailable")

    with monkeypatch.context() as context:
        context.setattr(statement_operations, "create_backup", fail)
        with pytest.raises(BackupError):
            import_statements(config, [preview()])
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementImport)) == 0
    assert import_statements(config, [preview()])[0].status == "imported"


def test_invalid_or_conflicting_inputs_do_not_back_up(engine, database_url, tmp_path, monkeypatch):
    config = settings(database_url, tmp_path)
    with Session(engine) as session, session.begin():
        accept_previews(session, config.shop_id, [preview()])

    def unexpected(*args, **kwargs):
        raise AssertionError("No backup should run for invalid/conflicting input")

    monkeypatch.setattr(statement_operations, "create_backup", unexpected)
    with pytest.raises(StatementError, match="blocking"):
        import_statements(config, [preview([source_row(Net="$0.01")])])
    with pytest.raises(StatementError, match="review"):
        import_statements(config, [preview([source_row(Amount="$2.00", Net="$2.00")])])


def test_migration_backed_up_before_upgrade_then_noop_skips_backup(
    engine,
    database_url,
    migration_config,
    tmp_path,
):
    config = settings(database_url, tmp_path)
    with Session(engine) as session, session.begin():
        accept_previews(session, config.shop_id, [preview()])
    command.downgrade(migration_config, "0002")
    record = initialize_statements(config)
    assert record.reason == "pre_migration"
    assert record.retain_through == "2035-12-31"
    with closing(sqlite3.connect(config.backup_dir / record.filename)) as snapshot:
        assert snapshot.execute("SELECT version_num FROM alembic_version").fetchone() == ("0002",)
        assert snapshot.execute("SELECT COUNT(*) FROM statement_entries").fetchone() == (1,)
    assert "statement_fee_classifications" in inspect(engine).get_table_names()
    assert initialize_statements(config) is None
    assert len(list(config.backup_dir.glob("*.json"))) == 1


def test_backup_failure_blocks_migration(
    engine,
    database_url,
    migration_config,
    tmp_path,
    monkeypatch,
):
    config = settings(database_url, tmp_path)
    command.downgrade(migration_config, "0002")

    def fail(*args, **kwargs):
        raise BackupError("Backup failed")

    monkeypatch.setattr(statement_operations, "create_backup", fail)
    with pytest.raises(BackupError):
        initialize_statements(config)
    assert "statement_fee_classifications" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert (
            connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar() == "0002"
        )


def test_migration_failure_rolls_back_ddl_but_preserves_backup(
    engine,
    database_url,
    migration_config,
    tmp_path,
    monkeypatch,
):
    config = settings(database_url, tmp_path)
    command.downgrade(migration_config, "0002")

    def fail(alembic_config, revision):
        alembic_config.attributes["connection"].exec_driver_sql(
            "CREATE TABLE must_rollback (id INT)"
        )
        raise RuntimeError("Synthetic migration failure")

    monkeypatch.setattr(statement_operations.command, "upgrade", fail)
    with pytest.raises(RuntimeError, match="Synthetic"):
        initialize_statements(config)
    assert "must_rollback" not in inspect(engine).get_table_names()
    assert latest_backup(database_url, config.backup_dir).verified


def test_fresh_initialization_needs_no_backup(tmp_path):
    config = settings(f"sqlite:///{tmp_path / 'new.sqlite3'}", tmp_path)
    assert initialize_statements(config) is None
    assert not config.backup_dir.exists()
    assert initialize_statements(config) is None


def test_classification_changes_are_backed_up(engine, database_url, tmp_path):
    from pumpkincarriageco.models import StatementFeeClassification

    config = settings(database_url, tmp_path)
    parsed = preview([source_row("Fee", "--", "-$0.20", "-$0.20", Title="Listing fee")])
    with Session(engine) as session, session.begin():
        accept_previews(session, config.shop_id, [parsed])
        # Disposable fixture simulates the initial importer, before fee annotations existed.
        session.query(StatementFeeClassification).delete()
    result = import_statements(config, [parsed])[0]
    assert result.status == "classified_existing"
    record = latest_backup(database_url, config.backup_dir).record
    with closing(sqlite3.connect(config.backup_dir / record.filename)) as snapshot:
        assert snapshot.execute("SELECT COUNT(*) FROM statement_entries").fetchone() == (1,)
        assert snapshot.execute(
            "SELECT COUNT(*) FROM statement_fee_classifications"
        ).fetchone() == (0,)


def test_cli_backup_failure_blocks_import(engine, database_url, tmp_path, monkeypatch, capsys):
    from test_statements import csv_bytes

    from pumpkincarriageco.services.statement_cli import main

    source_dir = tmp_path / "statements"
    source_dir.mkdir()
    (source_dir / "etsy_statement_2025_1.csv").write_bytes(csv_bytes([source_row()]))
    blocked_folder = tmp_path / "blocked"
    blocked_folder.write_text("A file cannot be used as a backup folder")
    monkeypatch.setenv("PCC_STATEMENTS_DATABASE_URL", database_url)
    monkeypatch.setenv("PCC_DATABASE_URL", "sqlite:///data/demo.sqlite3")
    monkeypatch.setenv("PCC_STATEMENTS_SHOP_ID", "test-shop")
    monkeypatch.setenv("PCC_STATEMENTS_BACKUP_DIR", str(blocked_folder))
    monkeypatch.setattr(
        "sys.argv", ["statement_cli", "import", "--directory", str(source_dir), "--confirm"]
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert "Backup failed" in capsys.readouterr().err
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StatementImport)) == 0
