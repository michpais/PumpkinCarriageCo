# Import and validate historical Etsy monthly statements

## Business problem and resulting behavior

Previously the application only displayed synthetic orders. It can now preview,
validate and explicitly accept downloaded Etsy monthly payment-account CSVs into
a separate real-data SQLite database. Users can inspect monthly categories,
missing coverage, import history and source-row evidence without changing their
OneDrive originals or connecting to Etsy.
The main app now opens saved Statements with a native sidebar linking Imports,
Backups and the separate Synthetic demo. Previously these workflows required
different launch commands and the main app only queried the synthetic table.

## Scope

- Strict UTF-8/header/date/USD/money/arithmetic validation; signed credits and
  description-only deposits handled separately from sales.
- Pure parser, shared transactional acceptance service, explicit CLI and separate
  Streamlit review/confirmation screen. All files in a batch preflight before any
  writes. Database failures roll back the batch.
- Shop/month uniqueness and full-row hash multiplicity make repeat imports safe
  while retaining legitimate duplicate fees. Reordered/BOM/newline equivalents
  are skipped; changed accepted months require review and never overwrite history.
- Minimized source tables retain validated financial values, recognized Etsy IDs,
  file/row hashes, source record numbers, versions, warnings and UTC observation
  times. Free text and buyer/card details are discarded before persistence.
- Ten-year retention markers, setup, backup/restore, definitions, synthetic sample
  output and operational limitations documented in statement-imports.md.
- Payment displays Etsy's original Type label instead of funding. Fee subtypes
  show charges, credits and net costs, derived from recognized titles. Revision
  0003 adds versioned annotations; confirmed equivalent uploads can classify older
  imports without modifying accepted records or adding duplicate activity.
- Integrated online backups: manual UI/CLI action, last-backup verification, and
  mandatory pre-change backups for actual imports/classification and existing
  schema upgrades. Failures block writes. Snapshots and manifests stay outside Git;
  no rotation, automatic restore, added schema, dependency or paid service.
- Native grouped sidebar with four file-based pages. Statements is the default;
  uploads and manual backup controls live on their own pages; the demo remains in
  Examples. The old upload launch command opens Imports with the same sidebar.
  Future pages require a script and one registration in app/navigation.py.

## Validation

- `uv run pytest`: 79 passed, including the existing demo tests, statement
  parsing/privacy/idempotence/conflict/atomicity tests, and Streamlit AppTest flows.
- `uv run mypy`: passed (30 source files).
- `uv run ruff check .` and `uv run ruff format --check .`: passed.
- `git diff --check`: passed.
- Alembic metadata check and upgrade/downgrade/re-upgrade exercised by tests on
  disposable SQLite databases. Existing demo schema behavior remains covered.
- Read-only preview against the owner's 26 local statements: 2,935 USD records,
  July 2024–August 2026, zero blocking issues and zero warnings. No real-data
  database was created/imported for this verification. September is not supplied.
- Read-only fee revalidation on 2026-10-20 classified all 1,709 Fee rows in the 26
  statements, with no unknown subtypes. Tests verify legacy schema upgrade,
  annotation-only classification, reordered rows/duplicates, charges and credits,
  current-version filtering, shop isolation and unchanged original financial facts.
- Backup tests cover an open WAL database, snapshot verification and corruption
  detection, broken-reference rejection, source/destination safeguards, repeat
  no-op behavior, pre-import/pre-classification/pre-upgrade state, backup failure
  gating in service/UI/CLI, and rollback of failed DDL with the snapshot retained.
- Reproduced the reported Arrow warning with a failing Streamlit regression test.
  Coverage now uses a null numeric count for missing months rather than mixing
  integers with the string `unavailable`. Imported empty months retain zero rows.
  The UI test verifies rendering without Streamlit's serialization fallback log.
  No database migration, stored-record change or reimport is required for this fix.
- Native navigation tests verify the real-data landing page, page-specific
  controls, no writes/backups on navigation, and no import authorization from
  leaving an unconfirmed upload. Demo tests switch through the native router with
  missing statement configuration. Existing import, backup and Arrow regression
  tests now exercise their respective pages.
- Streamlit workflow tested programmatically with synthetic files; no browser
  screenshot/visual layout review was performed. Synthetic output example is in
  statement-imports.md. No PostgreSQL, live Etsy or shared-hosting tests were run.

## Schema and reconciliation

Additive Alembic revision 0002 creates statement_imports, statement_entries and
statement_references. The real database defaults to data/shop.sqlite3 and must
remain separate from data/demo.sqlite3. Existing demo records are not converted.
Migrations and imports are explicit CLI/UI actions, never page-load effects.

Revision 0003 adds statement_fee_classifications without modifying accepted facts.
Users with a database from the initial implementation rerun `statement_cli init`,
which creates a verified backup before upgrading, then select and confirm their CSVs again
to obtain fee subtypes. Unclassified remains visible until that step. Original
import metadata and retention dates are unchanged; annotations have their own
version/time. No actual user database has been migrated by the implementation.
The navigation refactor adds no schema migration, dependency or settings change.
Existing statement IDs and database paths continue to select already imported data.
`init` takes and verifies its own pre-upgrade backup; there is no separate manual
copy requirement. No-op init skips backup. The migration environment now accepts
the guarded external connection so DDL runs under the same writer reservation.

These tables preserve statement source activity, not curated revenue/profit.
Deposits, buyer-tax movements, funding, fees and sale activity remain distinct.
No API totals are added. API retrieval is Part 2; matching and discrepancy
resolution are Part 3. Source day timezone is not verified. Changed month exports
need a future reviewed versioned-correction workflow, not deletion/reimport.

## Etsy, privacy, security, costs and side effects

No API endpoint, scope, credentials, OAuth, shop write, message, deployment, paid
service or AI call is introduced. Etsy's official statement/deposit guide was
checked on 2026-10-16; see capability documentation. api_util/conf.json is not read.
Original OneDrive statements are read-only inputs and are never copied into Git.

Names, emails, addresses, card hints and free text are not stored; reference IDs
remain traceable through Etsy and are not anonymous. No geography is imported.
Local SQLite is not encrypted/authenticated by this application: use a restricted
account and encrypted disk/backup storage. Streamlit remains loopback-only. Ten
years is a business policy represented as retain-through year + 10, December 31;
there is no automatic purge. Backups require the same retention review.
The default backup folder is `<your home>/Documents/PumpkinCarriageCo-Backups`;
optional `PCC_STATEMENTS_BACKUP_DIR` selects another private folder outside Git.
Manifests use a database-path identity hash, checksum, size, reason/time and source
retention marker; they contain no business records or database URL. No user backup
was created during development. Missing/changed latest snapshots are flagged.

No dependencies, lockfile, or demo environment defaults changed. Separate optional
statement environment variables were added to .env.example.

## Manual testing

1. Follow README statement setup; select an internal shop ID in .env. Do not use
   synthetic-demo. Keep statement and demo database paths distinct.
2. Preview a folder with the CLI; check month coverage, row counts and issues.
3. Explicitly run init; an existing schema upgrade must first create a verified
   backup automatically. A failed required backup must leave the schema unchanged.
4. Start `app/main.py` with Streamlit. It should open saved Statements without
   reuploading files. Navigate to Import statements, select CSVs and inspect review tables.
   No import should occur until the review checkbox and button are used.
5. Import, inspect source traceability/history/categories, then import the same
   files again. Counts must remain unchanged. Confirm missing months are unavailable.
   Check Payment is shown instead of funding and fee subtypes show charges,
   credits and net cost. With older accepted months, confirming the same files adds
   annotations only; source counts and totals must remain unchanged.
6. With synthetic disposable files only, change one amount and Net in an already
   accepted month. Confirm conflict blocks replacement and any other selected
   month in the same batch. Invalid arithmetic must also block acceptance.
7. Choose Synthetic demo in the Examples sidebar section; its behavior is unchanged
   and it continues to query only its separate synthetic database.
8. Use Back up now while Streamlit remains open. Confirm folder/time/file/status
   appear, then import a new month or classify an old one and confirm the latest
   backup updates. A no-op repeat should create no additional backup. In disposable
   testing only, make the backup folder unwritable and confirm the change is blocked.
9. Confirm sidebar groups Shop and Examples; switch between Statements, Imports,
   Backups and Synthetic demo. Viewing must create no source facts or backups.
   Mark an upload reviewed without importing, navigate away and return: it must
   require review again. The old statement_import.py launch still opens Imports.

## Rollback and limitations

Stop writers and revert the application code through a reviewed change. Preserve
the real database and backups; additive tables can remain unused. Do not downgrade
real storage: the 0002 downgrade drops imported source evidence. Any destructive
database operation needs separate human authorization. Restore only to a separate
path before explicitly selecting that copy.

Not included: API connection, scheduled/off-device backups or purge, full authentication,
PostgreSQL validation, import-attempt job history, changed-source replacement,
Stats import, API/statement matching, bank reconciliation or full profitability.
Only the observed CSV schema and USD are supported; other export layouts require
an adapter update. Hashes preserve identity, not proof of source authenticity.

## Opening the PR

Branch: `codex/phase-1-statement-import`; base: `main`.
No branch push was performed: AGENTS.md requires explicit push authorization.
GitHub CLI was not available in this environment. After authorization, push the
feature branch and open the GitHub compare page, using this file as the PR body:

```powershell
git push -u origin codex/phase-1-statement-import
```

If GitHub CLI is installed later:

```powershell
gh pr create --base main --head codex/phase-1-statement-import --title 'Import and validate historical Etsy monthly statements' --body-file docs/phase-1-part-1-pr.md
```

Do not merge or deploy without explicit human authorization.
