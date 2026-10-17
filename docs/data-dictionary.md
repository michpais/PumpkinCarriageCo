# Phase 0 data dictionary

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
