# PumpkinCarriageCo

Private shop analytics foundation for Godmother Minnie and her business advisor.
One Streamlit app provides saved statement reports, imports, backups and a
separate synthetic demo through native sidebar navigation. No Etsy client, OAuth,
background jobs, or live shop writes are implemented; API credentials are not read.

## Local setup (Python 3.12 + uv)

Run from the repository root in PowerShell:

```powershell
uv sync --locked
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set `PCC_STATEMENTS_SHOP_ID` in `.env` to a stable internal shop identifier before
using the real-data pages. Keep the identifier and database path already used for
existing imports. Then initialize the schema explicitly and start the app:

```powershell
uv run python -m pumpkincarriageco.services.statement_cli init
uv run streamlit run src/pumpkincarriageco/app/main.py
```

Open http://localhost:8501. The server binds to loopback without user
authentication; do not expose it to a network. Main opens **Statements** using
the existing real-data database. Real statement data stays separate from the demo.
The app reads data; migrations and demo seeding are explicit CLI steps.
Seeding is repeatable and only accepts an empty database or the existing demo shop.
`.env` is loaded by the settings layer; existing environment variables take precedence.

| Sidebar section | Page | Purpose |
| --- | --- | --- |
| Shop | Statements (default) | Saved coverage, history, monthly categories/fees and source records |
| Shop | Import statements | Preview and explicitly confirm uploads or fee classification |
| Shop | Backups | Back up now and inspect latest verification status |
| Examples | Synthetic demo | Original illustrative dashboard using the separate demo settings |

If you want the optional demo, prepare only its separate database first:

```powershell
uv run alembic upgrade head
uv run python -m pumpkincarriageco.services.demo
```

Missing statement settings do not prevent navigating to the demo. Opening or
switching pages never imports, classifies, seeds, migrates or backs up data.
If you leave an unconfirmed upload, reselect/review it before importing.

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run alembic check
```

SQLite defaults to `data/demo.sqlite3` (ignored by Git). Change `PCC_DATABASE_URL`
only for a separate local database. PostgreSQL is the intended future production
target; its driver, deployment, authentication, and integration tests are deferred.
`PCC_SHOP_ID` selects a shop explicitly and defaults to `synthetic-demo`.

## Historical monthly statements (Phase 1 Part 1)

Read [statement import and retention instructions](docs/statement-imports.md).
Preview needs no database, credentials, or configuration:

```powershell
uv run python -m pumpkincarriageco.services.statement_cli preview --directory 'C:\path\to\Monthly Etsy Statements'
```

Set `PCC_STATEMENTS_SHOP_ID` in your local `.env` to a chosen internal shop ID.
Leave the demo settings unchanged. Statement storage defaults to
`sqlite:///data/shop.sqlite3`, separate from `data/demo.sqlite3`.

```powershell
uv run python -m pumpkincarriageco.services.statement_cli init
uv run streamlit run src/pumpkincarriageco/app/main.py
```

Choose **Import statements**, select the CSVs, review validation and category totals, then confirm the
import. Alternatively, after reviewing the CLI preview:

```powershell
uv run python -m pumpkincarriageco.services.statement_cli import --directory 'C:\path\to\Monthly Etsy Statements' --confirm
uv run python -m pumpkincarriageco.services.statement_cli report
```

Original CSVs are read-only inputs. Accepted rows are minimized and retained for
10 years after their activity year; there is no automatic deletion. Missing
months are unavailable, not zero sales. These totals describe statement activity,
not verified revenue or profit. API matching is deferred to Part 3.

### Updating an existing statement database for fee breakdowns

Stop Streamlit before schema upgrades; `init` automatically creates and verifies
a backup before upgrading an existing schema. Keep the same
statement database path and internal shop ID used in your first test. Then run:

```powershell
uv run python -m pumpkincarriageco.services.statement_cli init
uv run streamlit run src/pumpkincarriageco/app/main.py
```

Revision 0003 adds a fee-classification table without modifying imported financial
records. Select the same original CSVs again and confirm **Import or classify
reviewed statements**. Existing months show **Fee classification available**;
confirming adds annotations, not duplicate activity. Fee descriptions were not
retained by the first importer, so reselecting the files is necessary. No reset
or deletion is needed. Payment now uses Etsy's label in the UI. Monthly fee
breakdowns show listing, processing, item/shipping transaction, shop setup and
unclassified fees, with charges, credits and net cost separately.

### Integrated statement backups

Use **Back up now** on **Backups**; Streamlit can remain open. The page
shows the backup folder, last successful backup and current verification status.
Imports/classification and schema upgrades create verified backups automatically
before changing existing storage. A failed required backup blocks the change.
Preview, unchanged repeat imports, and no-op initialization do not create backups.

The default folder is `<your home>/Documents/PumpkinCarriageCo-Backups`, outside
Git. Optionally set `PCC_STATEMENTS_BACKUP_DIR` in `.env` to another private folder
outside Git. No extra setting is required for the default. CLI manual backup:

```powershell
uv run python -m pumpkincarriageco.services.statement_cli backup
```

See [backup verification, retention and restore instructions](docs/database-backups.md).
No automatic deletion or restore is implemented.

## Adding a sidebar capability

Create a page script under `src/pumpkincarriageco/app/views/`, then register it in
the appropriate group in `app/navigation.py`. For example, after creating its file:

```python
st.Page(APP_DIR / "views/new_capability.py", title="New capability", url_path="new-capability")
```

The entry point owns `st.set_page_config`, the shared title and navigation.
Only the selected page executes. Pages call shared services; business rules and
guarded writes do not belong in navigation. New pages must have unique URLs.
The old `streamlit run src/pumpkincarriageco/app/statement_import.py` command is
supported as a compatibility entry point: it opens Import statements with the
same sidebar. Use `main.py` as the canonical command. This navigation change
needs no migration, reimport, `.env` update, or change to stored records.

## Documentation

- [Architecture and assumptions](docs/architecture.md)
- [Etsy capability research](docs/etsy-capabilities.md)
- [Data dictionary](docs/data-dictionary.md)
- [Metric definitions](docs/metrics.md)
- [Operations and Phase 1 prerequisites](docs/operations.md)
- [Review description and rollback](docs/pull-request.md)

The term 'Etsy' is a trademark of Etsy, Inc. This application is not endorsed or
certified by Etsy, Inc.
