# Statement database backups

The unified app's **Backups** sidebar page includes **Back up now**, a backup-folder display, last successful
backup time/file, retain-through date, and verification status. A manual backup
does not require stopping Streamlit. No backup occurs merely because the app is
opened or stopped. CLI alternative:

```powershell
uv run python -m pumpkincarriageco.services.statement_cli backup
```

## Destination and access

Default: `<your home>/Documents/PumpkinCarriageCo-Backups`. It matches the earlier
manual-backup folder convention. No `.env` change is needed unless a different
folder is wanted. Set `PCC_STATEMENTS_BACKUP_DIR` to an absolute private path to
override it; existing PowerShell variables still take precedence over `.env`.
The folder is created on the first backup, not when opening the app. Targets
inside any Git checkout or the active database's own directory are rejected.
Symlinks/junctions are resolved before checking the destination.

Backups contain the entire database, including all shops and retained reference
IDs. Use a restricted Windows account and encrypted disk/backup location. The
application does not set OS ACLs or encrypt snapshots. No credentials, raw source
files or OneDrive originals are accessed by the backup service. There is no paid
service, network upload, or automatic cloud replication. A local copy on the same
disk does not protect against disk loss; an independent protected copy is a
separate operational choice.

## Automatic protection

- Validated new imports or fee classification: back up once per changing batch
  before the first financial fact or annotation is written.
- Existing schema upgrades: `statement_cli init` backs up before DDL. It supports
  older schemas and passes its reserved connection to Alembic.
- Fresh initialization and already-current schemas need no backup. Invalid or
  conflicting batches and already-imported/classified repeats make no changes and
  create no backups. Preview and reports stay read-only.

UI/CLI write entry points reserve the SQLite writer before validation and backup.
The online backup reads committed data, including data in the write-ahead log,
while another connection keeps the write reservation. Other writers cannot change
the state between backup and the protected operation. The backup itself does not
change statement facts. Other open readers are supported; imports/migrations
remain subject to SQLite lock timeouts. Stop other writers before schema upgrades.

If copying, integrity checks, checksum verification, or metadata publication fails,
the pending import/classification/upgrade is blocked and an actionable controlled
error is shown. Source SQL and record values are not printed. Backup copying has
a 30-second deadline; retry after checking free space, folder access and competing
writers. If the protected operation subsequently fails, its transaction rolls back
and the pre-change backup remains available.

Use the supported `statement_cli init` command for real-data upgrades. Direct
Alembic commands are low-level tools and do not automatically invoke this backup
gate; they remain appropriate for disposable tests and the synthetic demo.

## Verification and inventory

Each snapshot has a generated UTC timestamp/UUID filename, with no overwrite of
older backups. Verification runs SQLite `integrity_check` and `foreign_key_check`,
then syncs the snapshot and records SHA-256 and size. A JSON sidecar records the
database-path identity hash, generated filename, reason, UTC timestamp, size,
checksum and retain-through date. It contains no business rows or database URL.
The JSON is synced before atomic rename publishes the success marker.

The UI finds the latest valid manifest for this database path and checks the
snapshot's size and checksum again. This confirms it still matches the snapshot
that passed SQLite checks at creation; it is not a repeated restore rehearsal.
Missing/changed snapshots produce a warning. It does not silently fall back to
an older snapshot when the latest one is damaged. Legacy manual copies without
manifests remain untouched but do not appear in this inventory. Changing the
database path or backup folder changes which inventory is displayed.

An interrupted attempt can leave an unverified SQLite file or `.json.pending`
file. These are not successful backup inventory entries. Nothing is deleted
automatically; incomplete copies still contain financial data and require private
handling and deliberate review. Keep each successful `.sqlite3` and `.sqlite3.json`
together when archiving or copying to another location.

## Retention and restore

Snapshots are marked to retain through the latest source-record retention date
inside them (end of activity year + 10). An empty/older schema without retention
records is marked through the end of backup year + 10. This is the agreed business
policy; there is no rotation or purge. Disk use grows with successful backups.
Expiry review must cover snapshots, sidecars, incomplete copies and any external
copies. OneDrive source files are never deleted or changed by this feature.

There is no automatic restore or overwrite button. To test a restore:

1. Choose a verified snapshot; keep its original backup and sidecar untouched.
2. Copy the SQLite snapshot to a **new** path outside the backup folder. Never
   overwrite the active database or modify a verified backup in place.
3. Stop writers and configure `PCC_STATEMENTS_DATABASE_URL` to that test copy,
   retaining the original internal shop ID. Run guarded `statement_cli init` only
   if the copied snapshot needs a schema upgrade; its own pre-upgrade backup is
   created under that new database identity.
4. Inspect source counts, history, periods, monetary totals and references in the
   app. A backup preceding an import/classification naturally lacks that change.
5. Select the original database again after testing. Promoting a restored copy
   over newer business data requires deliberate human review.

Development verification uses synthetic records and disposable databases, including
an open WAL database, backup failures, annotation-only changes, pre-migration
snapshots, DDL rollback and UI status. No user database backup or migration is
executed as part of implementation testing.

Implementation basis: [Python 3.12 SQLite backup API](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup)
and [SQLite's online backup documentation](https://www.sqlite.org/backup.html),
checked 2026-10-24. No Etsy endpoint, API scope or live shop operation is involved.
