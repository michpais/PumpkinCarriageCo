"""Verified SQLite snapshots and sidecar manifests; no purge or restore operations."""

import hashlib
import json
import os
import re
import sqlite3
import time
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

Reason = Literal["manual", "pre_import", "pre_migration"]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKUP_TIMEOUT_SECONDS = 30.0


class BackupError(ValueError):
    """Controlled messages contain no SQL, secrets or source record values."""


@dataclass(frozen=True)
class BackupRecord:
    database_id: str
    filename: str
    created_at: str
    reason: str
    sha256: str
    size_bytes: int
    retain_through: str


@dataclass(frozen=True)
class BackupStatus:
    record: BackupRecord
    verified: bool


def database_path(database_url: str) -> Path:
    try:
        url = make_url(database_url)
    except ArgumentError:
        raise BackupError("Invalid local database configuration") from None
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise BackupError("Backups require a local SQLite database file")
    if url.query:
        raise BackupError("SQLite URL query options are not supported for backed-up operations")
    return Path(url.database).resolve()


def database_id(source: Path) -> str:
    return hashlib.sha256(os.path.normcase(str(source.resolve())).encode()).hexdigest()


def backup_directory(source: Path, directory: Path) -> Path:
    target = directory.expanduser().resolve()
    # Reject both the development checkout and any other Git checkout, including symlink targets.
    if target.is_relative_to(PROJECT_ROOT) or any(
        (parent / ".git").exists() for parent in (target, *target.parents)
    ):
        raise BackupError("Choose a backup folder outside Git repositories")
    if target == source or target == source.parent:
        raise BackupError("Choose a backup folder separate from the active database folder")
    return target


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _check_snapshot(path: Path) -> str:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise BackupError(
                "Backup integrity verification failed; the pending change was blocked"
            )
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise BackupError("Backup contains broken references; the pending change was blocked")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        if "statement_imports" in tables:
            retained = connection.execute(
                "SELECT MAX(retain_through) FROM statement_imports"
            ).fetchone()
            if retained and retained[0]:
                return date.fromisoformat(retained[0]).isoformat()
    return date(datetime.now(UTC).year + 10, 12, 31).isoformat()


def create_backup(database_url: str, directory: Path, reason: Reason = "manual") -> BackupRecord:
    """Snapshot committed data, including WAL data, then publish a verified manifest."""
    try:
        source = database_path(database_url)
        if not source.is_file():
            raise BackupError("No statement database exists yet; initialize it before backing up")
        target_dir = backup_directory(source, directory)
        if reason not in ("manual", "pre_import", "pre_migration"):
            raise BackupError("Unsupported backup reason")
        target_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        identity = database_id(source)
        stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
        name = f"shop-{identity[:16]}-{stamp}-{uuid4().hex}-{reason}.sqlite3"
        destination = target_dir / name
        # Reserve a fresh path; never reuse or overwrite a prior backup.
        with destination.open("xb"):
            pass
        deadline = time.monotonic() + BACKUP_TIMEOUT_SECONDS

        def progress(status: int, remaining: int, total: int) -> None:
            if time.monotonic() > deadline:
                raise BackupError("Backup timed out; close other writers and retry")

        with (
            closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=5)) as origin,
            closing(sqlite3.connect(destination, timeout=5)) as snapshot,
        ):
            origin.backup(snapshot, pages=128, progress=progress, sleep=0.05)
        retained = _check_snapshot(destination)
        with destination.open("rb+") as stream:
            os.fsync(stream.fileno())
        checksum = file_hash(destination)
        record = BackupRecord(
            identity, name, now.isoformat(), reason, checksum, destination.stat().st_size, retained
        )
        if file_hash(destination) != checksum:
            raise BackupError("Backup checksum verification failed; the pending change was blocked")
        # Publish the success marker only after both files have been written and synced.
        pending = destination.with_suffix(".sqlite3.json.pending")
        with pending.open("x", encoding="utf-8") as manifest_stream:
            json.dump(asdict(record), manifest_stream, indent=2)
            manifest_stream.flush()
            os.fsync(manifest_stream.fileno())
        pending.rename(destination.with_suffix(".sqlite3.json"))
        return record
    except BackupError:
        raise
    except (OSError, sqlite3.Error, ValueError):
        raise BackupError(
            "Backup failed; check the backup folder permissions, free space and database health. "
            "The pending change was blocked"
        ) from None


def latest_backup(database_url: str, directory: Path) -> BackupStatus | None:
    """Return the last successful manifest, rechecking the snapshot size and checksum."""
    try:
        source = database_path(database_url)
        target = backup_directory(source, directory)
        identity = database_id(source)
        if not target.exists():
            return None
        for manifest in sorted(target.glob(f"shop-{identity[:16]}-*.sqlite3.json"), reverse=True):
            if manifest.stat().st_size > 16384:
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                record = BackupRecord(**data)
                if (
                    record.database_id != identity
                    or record.filename != manifest.name.removesuffix(".json")
                    or not re.fullmatch(r"[a-f0-9]{64}", record.sha256)
                    or not isinstance(record.size_bytes, int)
                    or record.size_bytes <= 0
                    or record.reason not in ("manual", "pre_import", "pre_migration")
                ):
                    continue
                if datetime.fromisoformat(record.created_at).utcoffset() is None:
                    continue
                date.fromisoformat(record.retain_through)
                snapshot = target / record.filename
                verified = (
                    snapshot.is_file()
                    and snapshot.stat().st_size == record.size_bytes
                    and file_hash(snapshot) == record.sha256
                )
                return BackupStatus(record, verified)
            except (OSError, ValueError, TypeError):
                continue
        return None
    except BackupError:
        raise
    except (OSError, ValueError):
        raise BackupError(
            "Backup history is unavailable; check the configured backup folder"
        ) from None
