# ADR 0001 — Local synthetic foundation

Phase 1 Part 1 adds a separate statement workflow; see ADR 0002 below. The
foundation decisions here remain the description of the synthetic demo.

Status: proposed for review, implemented on `codex/phase-0-foundation`.
Date: 2026-10-16.

## Discovery

The repository at `f80df84` contained AGENTS.md, .gitignore, and .python-version
(3.12), with no application, tests, dependencies, migrations, or documentation.
The checkout was clean and matched freshly fetched origin/main. No existing
business data or integration was assumed or inspected.

## Decision

Use Python 3.12, uv with a committed lockfile, and a src-layout package.
Streamlit handles presentation; services own date boundaries and workflows;
repositories own shop-scoped persistence queries; analytics owns pure integer-money
calculations. SQLAlchemy owns models; Alembic owns explicit schema changes.
Use SQLite locally; target PostgreSQL when deployment is approved. We have not
installed a PostgreSQL driver or claimed compatibility testing against a server.

Flow: Streamlit → dashboard service → shop-scoped repository → SQLAlchemy/SQLite;
the dashboard service also calls the pure metrics module.

The minimal schema contains shop configuration and **synthetic-only** order facts.
Do not turn demo_orders into an Etsy import table. Its USD/source checks prevent
silently mixing fixture data with production facts. The demo CLI seeds an isolated
database, never the UI; its transaction prevents partial installation.
No migrations, seeding, or API requests run automatically during a page load.

Use fixed September 2026 fixtures, USD, and America/New_York for the demo. These
are illustrative defaults, not claims about the real shop. Dates are inclusive
shop-local calendar dates, converted to half-open UTC intervals. Previous periods
use the same number of local calendar days, including across DST changes.
Amounts are integer cents, formatted using Decimal. API Money objects will need
validated amount/divisor/currency conversion in Phase 1; never assume divisor=100.

## Boundaries and deferred choices

- No Etsy HTTP library yet: install httpx when a verified adapter needs it.
- No direct Pandas/Plotly dependency yet: the demo has four scalar metrics;
  Streamlit already brings Pandas transitively. Add direct dependencies when used.
- No generic tenant, AI-provider, auth, scheduler, or write-approval framework.
- No production access flags: there is no callable Etsy read/write implementation.
- Local loopback only, no authentication. Choose private hosting, OIDC identities,
  owner/advisor roles, and session protections before any shared deployment.
- No buyer PII or credentials in schema, fixture, tests, or screenshots.

## Phase 1 data architecture proposal (not migrated)

Separate import/sync runs from immutable, minimized source records and curated
entities. Each run records shop, source, schema version, file hash/cursor, status,
observation time, and reconciliation outcomes. Deduplicate source facts by
shop + source type + upstream ID; changed payloads become timestamped versions.
CSV row identity must be designed against approved sample files, not row position.
Keep receipts, transaction lines, payments, refunds, and ledger entries at their
own grains; link them rather than summing overlapping amounts.

Maintain listing/variant snapshots and effective-dated costs separately from
sales facts. A change event records actor, reason, before/after, source, observation
time, effective time, and precision. External snapshot changes only establish an
interval, not an exact edit time. Enforce append-only change history through a
dedicated service and database permissions when implemented.

Raw staging is not permission to retain full buyer payloads indefinitely. Decide
necessary fields, encrypted storage, access restrictions, and retention/deletion
before the first real import. Quarantine invalid records and report discrepancies.
Keep API payloads, authorization headers, database URLs, and raw CSV values out of
logs and browser errors. Tokens belong in an approved encrypted secret store, not
this database foundation.

## Consequences

The foundation is small, locally reproducible, and independently testable. It is
not an accounting system or production dashboard. The deliberate synthetic table
will coexist with new real-data models in a future migration rather than require
unsafe reinterpretation of example records. PostgreSQL, retention, access control,
and source reconciliation remain gates for real data.

## ADR 0002 — Local statement source records

Date: 2026-10-16. Implemented for review on `codex/phase-1-statement-import`.

The owner authorized a read-only statement importer, separate real-data SQLite
storage, minimized buyer fields and ten-year financial retention. The importer
never reads API credentials. Original OneDrive files remain unchanged.

Use `data/shop.sqlite3` via separate statement settings. The demo remains in
`data/demo.sqlite3`. Revision 0002 adds statement imports, entries and recognized
references; no demo facts are converted. UI and CLI call the same pure parser
and transactional acceptance service. Page loads never migrate or import.

Preserve source evidence through byte/row hashes and CSV record references,
without copying unrestricted raw text into staging. The normalized source facts
are append-only through application workflows. Local SQLite does not provide
database-role enforcement of immutability. Changed accepted months require a
future reviewed versioning workflow. API facts will have separate tables in this
same real-data database and later reconciliation links; this part does not yet
build a unified sales fact or add API amounts to statement totals.

Classification is intentionally conservative: source Types map to separate
categories; unknowns remain unclassified. Keep exact signed cents and missing
values. Retain source dates without inferring a timezone or exact timestamp.
Store parser/classification versions and warnings. Source hashes do not make the
records anonymous; retained order IDs permit tracing through Etsy.

Ten-year retention is represented as an inclusive retain-through date at the end
of activity year + 10. No purge is implemented. Disk protection is an operating
requirement; integrated statement backups are described below.
Shared hosting, OAuth, API caching/retention terms, Stats, job-attempt history,
full accounting and API reconciliation remain separate work. Details and limits
are in [statement-imports.md](statement-imports.md).

### Fee classifications (2026-10-20 refinement)

The owner requested clearer Payment labeling and fee subtypes before pushing.
Retain the existing category storage code for compatibility and map it to Payment
in presentation/CLI output. Add revision 0003 for versioned, append-only fee
annotations. Original descriptions were deliberately discarded, so existing
imports cannot be classified from stored amounts alone. User-confirmed equivalent
source uploads add hash/occurrence-matched annotations without rewriting financial
facts or deduplicating away legitimate repeats. Current reports use one annotation
version and keep unclassified fees visible. No real database migration is performed
as part of development; the user applies it explicitly after backup.

### Integrated SQLite backups (2026-10-24 refinement)

Use Python's SQLite online backup API and verified sidecar manifests outside Git.
Manual UI/CLI snapshots can run while the app is open. Backed-up write entry
points reserve the SQLite writer before validation, snapshot the committed state
using a second read-only connection, then perform the import/classification or
migration in the original transaction. Backup failure prevents the change; failed
migrations roll back DDL under the explicit transaction. No-op work skips backup.

Manifests avoid adding backup metadata tables to the database that must be backed
up before migrations. They record only path identity hash, generated filename,
reason, UTC creation time, checksum, size and retention date. Verification uses
SQLite integrity/foreign-key checks, fsync and checksum; UI history rechecks size
and checksum. No main schema migration, dependency, scheduler, encryption, cloud
service, purge or restore feature is added. Backup files include all shops in the
configured database. Operational details are in database-backups.md.

### Native sidebar navigation (2026-10-24 refinement)

The user selected native `st.navigation`/`st.Page` after comparing automatic
folder discovery and a custom selector. `app/main.py` is now the shared entry
point with Statements (default), Import statements, Backups, and Synthetic demo
under Examples. Explicit registration in `app/navigation.py` fixes order/groups
and makes future pages a file plus one registration entry. File-based views are
tested by switching through real native routing in AppTest.

The former combined statement UI is split by responsibility. Shared statement
UI helpers own settings, safe database errors and exact-money formatting. Business
services, models, migrations, source files and existing configuration are unchanged.
The previous statement entry point remains a thin alias opening Imports with the
same navigation. Only the selected page executes: statement configuration failures
do not prevent selecting the demo. Navigation never triggers writes or backups.
The demo retains its own database/settings and synthetic warnings; new financial
KPIs, Etsy access and hosting remain outside this change. Design and execution
notes are in docs/superpowers/specs and docs/superpowers/plans.

Streamlit API verification: [native navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation)
and [page registration](https://docs.streamlit.io/develop/api-reference/navigation/st.page),
checked against the installed 1.66.0 API documentation on 2026-10-24.
