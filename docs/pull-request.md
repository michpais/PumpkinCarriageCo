# Establish the Phase 0 local analytics foundation

## Business problem and result

The repository had no runnable application or data foundation for evaluating shop
profit. This change establishes a local Streamlit demo with explicit financial
definitions, source labeling, and reviewable database migrations. It enables the
owner and advisor to evaluate the structure before any real shop access.

## Scope and decisions

- Python 3.12, uv-managed dependencies/lockfile, src package layout.
- Streamlit presentation separated from services, repositories, and analytics.
- SQLAlchemy SQLite foundation, shops plus synthetic-only order facts, initial
  Alembic migration, scoped queries, UTC timestamps and exact integer cents.
- Explicit repeatable fixture CLI, date/prior-period comparison, safe setup errors,
  metric definitions, source observation label, and no network client.
- Official Etsy research dated 2026-10-16, endpoint/scope/access matrix, documented
  unsupported capabilities and Phase 1 gates. See docs/etsy-capabilities.md.
- GitHub Actions workflow for locked environment, lint/format, typing, tests, migrations.

## Validation and sample output

Local Python 3.12.12 on Windows:

- `uv sync --locked`: reproducible environment check.
- `uv run ruff check .` and `uv run ruff format --check .`.
- `uv run mypy`: strict source checks.
- `uv run pytest`: **10 passed**; monetary/refund/currency handling, migration upgrade/check/downgrade,
  source uniqueness, foreign keys, seed repeatability/conflict detection, shop isolation,
  local dates, invalid timestamps/ranges, configuration and Streamlit app flows.
- `uv run alembic upgrade head`, `uv run alembic check`, and the fixture CLI.
- Local Streamlit server startup and HTTP health smoke check: `ok`.

September 1–30, 2026 synthetic fixture output:

| Orders | Units | Item sales | Net revenue | Contribution |
| --- | --- | --- | --- | --- |
| 4 | 6 | $204.00 | $224.00 | $136.00 |

The UI warns SYNTHETIC DEMO, shows Etsy disconnected, and excludes labor/overhead
from contribution. Prior-period synthetic data is empty. Tests run the actual page
using Streamlit AppTest. Browser visual review, remote CI, PostgreSQL, and live Etsy
integration were not run; no claims of production readiness are made.

## Schema and reconciliation

Migration 0001 creates shops and demo_orders. All rows are synthetic; no existing
schema or data was migrated. Database files are ignored. No importer exists and
there is no risk of interpreting this seed as historical Etsy sales. Phase 1 must
introduce separate source-run/raw/curated models and reconcile overlapping receipts,
payments, refunds and ledger entries before presenting real financial totals.

## Security, scopes, costs and external effects

No scopes requested, secrets stored, buyer PII ingested, paid services added, shop
connected, shop modified, deployment performed, PR merged or self-approved.
The local server binds to 127.0.0.1 and telemetry is disabled. Authentication and
owner/advisor roles must precede shared deployment. Future writes require preview,
exact approval, audit history and separate runtime authorization.

## Manual test and rollback

Follow README setup, open http://localhost:8501, compare the sample totals, choose
an empty period, then an invalid date range. Verify clear messages and no traceback.
Select a nonexistent PCC_SHOP_ID to check the safe setup error.

Stop the local server to end testing. Return to the base code or use another fresh
demo database to rollback. Do not downgrade retained data without explicit approval:
0001 downgrade drops both business tables. No production rollback is required.

## Limitations and follow-up

Synthetic USD only; no real imports, API client/OAuth, authentication, production
database driver, paid AI, schedules, change history, listings editor, traffic,
review matching or messaging. Contribution is not profit. Confirm the prerequisites
in docs/operations.md before a separate Phase 1 PR.

## Publication

GitHub CLI is unavailable in the implementation environment. This is a local
PR-ready feature branch; no remote PR has been created. After the owner authorizes
publishing the feature branch, run from the repository root with authenticated gh:

```powershell
git push -u origin codex/phase-0-foundation
gh pr create --base main --head codex/phase-0-foundation --title "Establish Phase 0 local analytics foundation" --body-file docs/pull-request.md
```

Opening a PR does not authorize merging, deployment, or Etsy connection.
