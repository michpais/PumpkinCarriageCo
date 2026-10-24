# Monthly statement import

Phase 1 Part 1 accepts Etsy monthly payment-account CSVs. It does not connect to
Etsy, use API scopes, read API secrets, import Stats.xlsx, or implement accounting
profit. Stats imports remain a separate follow-up after their schema is reviewed.

## Workflow

1. Run the README preview command against the statement folder. Preview only opens
   files in binary read mode and never opens a database. It reports month, count,
   SHA-256 and controlled issue codes; it does not echo descriptions or buyer data.
2. Choose `PCC_STATEMENTS_SHOP_ID`, an internal ID of at most 100 characters, in
   `.env`. Do not use `synthetic-demo`. No Etsy ID or secret is needed. Later API
   mapping can associate this internal shop with its numeric Etsy ID.
3. Keep `PCC_STATEMENTS_DATABASE_URL=sqlite:///data/shop.sqlite3`. The default demo
   database and any database containing synthetic demo facts are rejected. These
   are real financial records even while the application is under development.
4. Stop other writers for schema upgrades and run the explicit
   `statement_cli init` command. It applies Alembic through revision 0003. There
   is no migration or import on page load.
   Existing schema upgrades require an automatic verified backup before any DDL.
5. Open the separate statement app or use `import --confirm`. The UI displays
   months, existing import status, validation issues, category counts and amounts
   before acceptance. Changing the selected files resets its confirmation box.
6. Review history, source hashes, category totals, warnings and coverage. Choose
   the coverage range explicitly; a missing month displays `missing` and a null
   row count, never zero activity. Imported empty statements have zero rows.
   The row-count column stays numeric to avoid Streamlit/Arrow serialization
   fallback warnings. The current month may be incomplete.

All selected files must pass blocking validation. A conflicting month blocks the
entire selected batch. Accepted records and their references commit in one
transaction; a database failure rolls back the batch. Repeated equivalent months
are reported as already imported, without altering the accepted source provenance.
Successful imports are durable history. Failed previews/attempts are shown to the
operator but are not retained as a job ledger in this part.

## Supported source schema and identity

UTF-8 (optional BOM), comma-separated CSV, strict header order:

`Date,Type,Title,Info,Currency,Amount,Fees & Taxes,Net,Tax Details`

Filename: `etsy_statement_YYYY_M.csv` (one- or two-digit month). All activity dates
must fall within that month. English month-name dates are parsed independently of
the operating system locale. Date-only source values remain date-only; the source
timezone is **unverified**, and no midnight UTC timestamp is fabricated. The shop
configuration initially uses America/New_York as an explicit local assumption.

Only USD is currently supported. Files are capped at 20 MiB. Money accepts exact
two-decimal values with optional `$`, leading minus, and valid thousands groups;
the placeholder `--` becomes NULL, not a measured zero. Values over $10 billion
are rejected. Invalid encoding, schema, row width, date, currency, amount,
arithmetic, or unsupported deposit format blocks acceptance. CSV/formula text is
not executed. Raw input values never appear in validation errors.

Each accepted shop/month is unique. A byte hash records the accepted file. A
semantic hash over the sorted multiset of complete source-row hashes recognizes
the same month after BOM, newline, quoting or row-order changes. Row multiplicity
is retained: two identical legitimate fees remain two fees. Different content
for an accepted month is a conflict, including a changed count of identical rows.
There is deliberately no replacement, delete, or auto-correction operation.

`source_row` counts CSV records starting at 2 after the header, not physical text
lines inside a quoted multiline record. The file hash, month, row number, row
hash and occurrence identify original evidence. The original file remains the
authoritative full-text evidence; the application stores no raw copy. For a changed
export, compare source files outside the application before designing an approved
versioned correction workflow. Never delete an accepted month to bypass conflict
handling. Concurrent duplicate writers are protected by database unique constraints;
one may receive a safe database error and can retry after the other completes.

## Categories and amount interpretation

These are statement classifications, not revenue recognition rules:

| Etsy Type | Category (storage code except Payment display label) | Interpretation |
| --- | --- | --- |
| Sale | sale | Statement sale activity, not item-only revenue |
| Refund | refund | Signed refund activity |
| Fee | fee | Signed charges and credits |
| Shipping | shipping | Signed label charges, adjustments and credits |
| Tax | tax | Buyer-tax movements; not seller revenue |
| Buyer Fee | buyer_fee | Separate buyer-paid fee movements |
| Marketing | marketing | Marketing charges/credits |
| Payment | Payment | Payments toward the Etsy bill; excludes customer sales |
| Deposit | deposit | Transfer to bank; not revenue |
| Other | unclassified | Warning, retained separately for review |

For nondeposit rows, at least Amount or Fees & Taxes and a numeric Net must be
present. Validate `Net = Amount + Fees & Taxes`, treating an absent component as
zero only for this check. Preserve original placeholders in storage. Credits
remain positive; charges remain negative. A category subtotal is NULL when that
column has no supplied values. No cross-category profit total is produced.

Current deposits have `--` in the three numeric columns. Extract a positive exact
amount only from the entire recognized title `$N.NN sent to your bank account`;
keep it in `deposit_minor`, separate from NULL statement Net. Different deposit
formats or populated deposit numeric columns require an adapter update. No
opening/closing balance or bank-settlement reconciliation is claimed.

Unknown Types become `unclassified`; unrecognized Tax Details receive a warning
and are discarded. Warning codes and source-row references remain in import
metadata. Free text is never used to guess revenue, product attribution or PII.

### Fee subtypes and existing imports

The UI and CLI report display **Payment**, matching Etsy Type `Payment`. The old
internal storage code `funding` remains for database compatibility; accepted rows
are not rewritten just to change a label.

For Type `Fee`, title rules identify Listing, Payment processing, Transaction —
item, Transaction — shipping, and Shop setup. Credit descriptions map to the
same subtype as the corresponding charges. An unrecognized title remains
Unclassified and produces a nonblocking warning. Marketing and postage are not
included in these fee subtotals. No fee rate or type is guessed from the amount.

Fee breakdowns group by statement month and subtype. Charges are the positive
magnitude of negative Fee Net amounts; credits are positive Fee Net amounts.
Net cost = charges − credits, so a credit-only subtype can have negative cost.
These are supplementary views of the same source entries, never additional costs
to add to the existing Fee category total. They use recorded amounts, not current
fee rates. Preview and saved reports apply the same definitions. CLI `report`
now returns `monthly_categories` and `fee_subtypes` collections with cents fields.

Revision 0003 only adds `statement_fee_classifications`. It does not modify the
accepted statement tables. Existing fees initially display Unclassified because
their titles were discarded for privacy. Stop the app, rerun `statement_cli init`
(which automatically backs up an existing schema before upgrading), then select the original files again
and confirm **Import or classify reviewed statements**. The preview shows **Fee
classification available**. Equivalent reordered files also work: annotations
match row SHA-256 plus occurrence, not the new upload's row position.

After confirmation the service inserts append-only annotations with rule version
`fee-titles-v1` and an aware UTC observation time. It changes no source amounts,
IDs, counts, hashes, timestamps, original import warnings or retention dates.
Subsequent imports skip the already classified rows. Changed source months still
conflict; no reset/delete/reimport workaround is needed or permitted. Classification
requires the same batch validation and confirmation as a new import. There is no
automatic real-data migration or classification on page load. Future rule versions
can add annotations while preserving earlier ones; current reports select only
the current rule version and never count annotations as financial activity.

On 2026-10-20 a read-only revalidation of the 26 source files recognized all 1,709
Fee rows: 573 listing, 369 processing, 398 item transaction, 368 shipping transaction,
one shop setup; no unclassified fees or validation warnings. Counts include credit
rows. The user's existing real database was not migrated or changed for this check.

## Privacy, retention, and backup

Original OneDrive statements are never edited, renamed, moved, or deleted. No
source copy is placed in Git. Local `data/`, SQLite files, `.env`, and caches are
ignored. The importer does not read `api_util/conf.json` or need its credentials.

Before persistence, discard Title, Info, Tax Details, unknown Type strings, names,
emails, card hints, address text and all other arbitrary fields. Retain recognized
numeric Order/Listing/Label references only, plus validated dates, categories and
monetary strings. Source-row hashes cover original fields but do not reveal them.
Hashes and Etsy IDs still link records to source evidence, so this is minimized
financial data, not anonymous data. No geography is imported in Part 1.

Retention is **10 years after the activity calendar year**. A 2024 statement is
marked retain-through 2034-12-31. This is the agreed business policy, not a claim
about legal or Etsy API retention requirements. There is no automatic purge or
deletion UI. API data retention must also be checked against applicable API terms
when Part 2 is implemented. Source dates, not import dates, determine retention;
reimporting does not extend the period. Metadata and references follow their
source records. Expiry review must cover backups as well as the active database;
it must not delete or alter the owner's OneDrive source files.

Storage is local SQLite without application-level encryption or authentication.
Use an access-restricted Windows account and encrypted disk, keep the server bound
to loopback, and do not expose it through shared hosting. The app now provides
online **Back up now** and verified automatic backups before actual imports,
classification or existing-schema upgrades. No database shutdown is required for
backups. Use the guarded CLI `init` for statement migrations. See
[database-backups.md](database-backups.md) for verification, destination settings,
failure handling, ten-year markers and deliberate restore instructions. There is
no automatic purge or restore. Encryption/key management and shared-user
authentication remain future work. No paid services are required.

## Verification and limitations

Automated tests use synthetic CSVs and disposable databases. They cover exact
money, signed credits, deposit formats, privacy, deduplication with multiplicity,
conflicts, atomicity, source immutability, shop isolation, migrations and the UI.
A read-only validation on 2026-10-16 found 26 local statements (July 2024 through
August 2026), 2,935 USD rows, no blocking issues or warnings. This verifies adapter
compatibility, not source completeness or agreement with Etsy. September 2026 is
not supplied. No real-data import is performed as part of code validation.

Synthetic example: one Sale row with Amount `$10.00`, Fees & Taxes `--`, Net
`$10.00` and two identical Fee rows with Fees & Taxes/Net `-$0.20` imports as three
source entries. Category results are sale Net `$10.00` and fee Net `-$0.40`.
Importing it again inserts zero entries. A missing next month remains unavailable.

Official basis: Etsy says a monthly statement contains payment-account activity;
deposit availability and timing differ from the selected period's activity.
Verified 2026-10-16 against [Etsy's statement/deposit guide](https://help.etsy.com/hc/en-us/articles/360016389113-How-to-Calculate-Your-Etsy-Payments-Deposit-Amount).
No API endpoint or scope is used. Full API/statement matching is Part 3, after
Part 2 OAuth and read-only retrieval. Costs, labor, Stats and full revenue/profit
calculations remain outside this PR.
