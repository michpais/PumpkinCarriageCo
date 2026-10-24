# Local operation and Phase 1 gates

The canonical app command is `uv run streamlit run src/pumpkincarriageco/app/main.py`.
It opens saved Statements; use the sidebar for Imports, Backups and the separate
Synthetic demo. Existing statement `.env` settings and data stay unchanged. The
older statement entry command remains supported, opening Imports. This UI-only
navigation refactor needs no schema migration or reimport.

For the implemented Phase 1 Part 1 workflow, use
[statement-imports.md](statement-imports.md) and the README's separate statement
commands. The demo instructions and original pre-integration gates below remain
applicable to the demo and later API work. No API configuration is used for CSV
imports. Do not run demo seeding against a real-data database.

Statement backups are now integrated: use **Back up now** or `statement_cli backup`.
Actual writes and upgrades through `statement_cli init` require a verified
pre-change backup. Follow [database-backups.md](database-backups.md). The manual
closed-copy instructions below are for the original demo workflow.

## Running and changing the database

Follow README.md from the repository root. uv sync --locked reproduces Python 3.12
dependencies. Only PCC_DATABASE_URL and PCC_SHOP_ID are read from .env/environment;
there are no API credentials to configure in Phase 0. Do not paste secrets into
source control or this chat.

Before migration, verify the configured database is your local demo. Run
`uv run alembic current`, `uv run alembic upgrade head`, then `uv run alembic check`.
The app reports a safe setup error when the schema or selected shop is absent.
It does not print connection strings or raw exceptions. No data import UI exists.

For a SQLite backup, stop the app and any CLI writers, then copy the entire closed
database to an access-restricted location outside the repository. Restore with all
writers stopped by configuring PCC_DATABASE_URL to a copy of the backup, running
`uv run alembic current`, and verifying the demo totals. Do not restore over a
database containing newer data. PostgreSQL backup procedures are deferred until
a hosting/database choice is approved.

For rollback of the demo, stop the server and return to the prior feature commit,
or use a fresh separate demo database. The initial downgrade drops demo_orders
and shops; it is destructive and requires explicit authorization for any retained
database. Tests exercise downgrade only on disposable temporary databases.

## Before Phase 1

1. Confirm owner-led Seller App eligibility in Etsy's portal, or the approved
   Personal App route if applicable. Do not create another app without checking
   existing app ownership/status. Confirm the internal advisor access arrangement
   remains within the approved use case.
2. Approve the first read-only scope set: listings_r and transactions_r; add
   shops_r only if private shop/readiness settings are needed. Confirm shop ID,
   currency, timezone, permitted historical range, and exact data fields.
3. Select a registered HTTPS OAuth callback, encrypted token store, key ownership,
   refresh/reconnect behavior, and who can authorize the shop. Build PKCE and
   single-use state, mock tests, and credential/PII redaction before connection.
4. Provide sanitized representative statement/order/Stats exports and agree
   accounting basis, refund/fee treatment, COGS/labor assumptions, and retention.
   Do not assume monthly statement schemas or API coverage match all exports.
5. Before shared hosting or real buyer data: select secure authentication, owner
   and advisor identities/roles, private access, backups, retention/deletion,
   incident handling, and any recurring cost. No hosting is configured here.
6. Reverify current endpoints, app restrictions, policies, and quota in the portal.
   Add integration adapters with mocks, overlap-window cursors, idempotent imports,
   source freshness, and reconciliation; get separate approval to connect.

No production shop connection, deployment, paid service, AI usage, notification,
or live shop modification was performed. Shared deployment is not part of Phase 0.
