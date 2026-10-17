# PumpkinCarriageCo

Private shop analytics foundation for Godmother Minnie and her business advisor.
The Phase 0 dashboard runs on synthetic USD data. Phase 1 Part 1 adds a separate
local monthly-statement importer. No Etsy client, OAuth, background jobs, or live
shop writes are implemented; API credentials are not read by this importer.

## Local setup (Python 3.12 + uv)

Run from the repository root in PowerShell:

```powershell
uv sync --locked
Copy-Item .env.example .env
uv run alembic upgrade head
uv run python -m pumpkincarriageco.services.demo
uv run streamlit run src/pumpkincarriageco/app/main.py
```

Open http://localhost:8501. The server binds to loopback; this is a local demo
without user authentication. Do not expose it to a network. Keep real statement
data in the separate importer database described below, not the demo database.
The app reads data; migrations and demo seeding are explicit CLI steps.
Seeding is repeatable and only accepts an empty database or the existing demo shop.
`.env` is loaded by the settings layer; existing environment variables take precedence.

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
uv run streamlit run src/pumpkincarriageco/app/statement_import.py
```

Select the monthly CSVs, review validation and category totals, then confirm the
import. Alternatively, after reviewing the CLI preview:

```powershell
uv run python -m pumpkincarriageco.services.statement_cli import --directory 'C:\path\to\Monthly Etsy Statements' --confirm
uv run python -m pumpkincarriageco.services.statement_cli report
```

Original CSVs are read-only inputs. Accepted rows are minimized and retained for
10 years after their activity year; there is no automatic deletion. Missing
months are unavailable, not zero sales. These totals describe statement activity,
not verified revenue or profit. API matching is deferred to Part 3.

## Documentation

- [Architecture and assumptions](docs/architecture.md)
- [Etsy capability research](docs/etsy-capabilities.md)
- [Data dictionary](docs/data-dictionary.md)
- [Metric definitions](docs/metrics.md)
- [Operations and Phase 1 prerequisites](docs/operations.md)
- [Review description and rollback](docs/pull-request.md)

The term 'Etsy' is a trademark of Etsy, Inc. This application is not endorsed or
certified by Etsy, Inc.
