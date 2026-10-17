# Phase 0 data dictionary

The original tables below remain synthetic. Revision 0002 adds the separate
statement source tables documented after them; real facts never enter demo_orders.

Migration: `0001`. Physical SQLite timestamps are naive UTC; the ORM accepts only
aware timestamps, normalizes to UTC, and restores UTC tzinfo on reads. Do not write
raw local timestamps into these tables. Business effective time is ordered_at;
observation time is observed_at. Fixtures are explicitly synthetic.

| Table / grain | Fields and constraints |
| --- | --- |
| shops: one configured shop | id (internal string PK, not necessarily an Etsy numeric ID), name, IANA timezone, ISO currency |
| demo_orders: one synthetic order | integer id; shop_id FK; source_id unique within shop; source fixed to synthetic; currency fixed to USD; ordered_at; observed_at; positive units |
| demo_orders monetary facts | item_sales_minor (post-discount, pre-refund), refunds_minor (seller revenue refunded including shipping), shipping_income_minor, fees_minor, postage_minor, cogs_minor; nonnegative integer cents |
| alembic_version: migration state | managed by Alembic; not business data |

Foreign keys are enabled on every application SQLite connection. Queries require
shop_id. Synthetic order costs are attributed to an order solely for the demo.
They do not model payment timing, shared overhead, tax, BOMs, variants, or stock.
No customer name, email, address, OAuth token, API key, or real shop ID is stored.

Source IDs are stable (`demo-order-1` through `demo-order-4`); the fixture observation
timestamp is 2026-10-01T00:00:00Z. It is not the last successful Etsy sync time.
Future source-run, raw/staging, and curated grains are proposed in architecture.md;
no historical imports or general importer exist in Phase 0.

## Phase 1 Part 1 (migration 0002)

| Table / grain | Fields and constraints |
| --- | --- |
| statement_imports: one accepted shop/month | Shop FK; period is first day of source month; unique shop/month and shop/file hash; accepted source basename; byte and semantic SHA-256; parser/classification versions; USD; UTC observation timestamp; row/warning counts; controlled validation JSON; inclusive retain-through date |
| statement_entries: one source CSV record occurrence | Import FK; CSV record number; full-row SHA-256; occurrence within identical rows; activity date at day precision; allowlisted category; validated original Amount/Fees & Taxes/Net strings; nullable signed integer cents for each numeric column and separate deposit cents |
| statement_references: one recognized ID per entry/kind | Entry FK; order/listing/label kind; numeric source ID as text; unique entry/kind/ID |

Entries are shop-scoped through their required import parent; all report queries
filter the parent shop. The source row starts at 2 after the CSV header. Import
hashes and occurrence counts retain legitimate duplicate rows while repeat files
remain idempotent. See statement-imports.md for month conflicts and privacy.

Retain-through is December 31 of source year + 10. No names, emails, addresses,
card fragments, free-text titles/info/tax details, or geography are stored. Source
reference IDs are retained intentionally. There is no raw CSV/blob or secret table.
