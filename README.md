# PumpkinCarriageCo

Private shop analytics foundation for Godmother Minnie and her business advisor.
Phase 0 runs entirely on synthetic USD data. No Etsy client, credentials, OAuth,
background jobs, or production writes are implemented.

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
without user authentication. Do not expose it to a network or ingest real buyer
data. The app reads data; migrations and demo seeding are explicit CLI steps.
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

## Documentation

- [Architecture and assumptions](docs/architecture.md)
- [Etsy capability research](docs/etsy-capabilities.md)
- [Data dictionary](docs/data-dictionary.md)
- [Metric definitions](docs/metrics.md)
- [Operations and Phase 1 prerequisites](docs/operations.md)
- [Review description and rollback](docs/pull-request.md)

The term 'Etsy' is a trademark of Etsy, Inc. This application is not endorsed or
certified by Etsy, Inc.
