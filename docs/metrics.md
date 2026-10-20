# Metric definitions

These definitions apply to synthetic USD orders in an inclusive shop-local date
range. Deltas are absolute differences against the immediately preceding equal
number of local calendar days. Financial arithmetic uses integer cents throughout.
Do not mix currencies or interpret missing source data as a zero business result.
An empty demo selection shows zeros and an explicit no-orders message.

| Display | Definition |
| --- | --- |
| Orders | Count of synthetic order facts in period |
| Units ordered | Sum of ordered units, not reduced for refunds |
| Item sales | Item revenue after discounts, before refunds; excludes shipping, tax and VAT |
| Net revenue | Item sales + shipping income − seller revenue refunded |
| Contribution | Net revenue − Etsy fees − postage − COGS |
| Observed | Latest source observation timestamp among selected records; absent when empty |

Refund amounts exclude tax refunded by the marketplace. Fixtures have no refunds;
unit tests exercise partial refunds and exact-cent arithmetic. Fees are positive
costs and any eventual fee credits need separate reconciliation rules.

Gross sales before discounts, recognized revenue under a chosen accounting basis,
average order value, contribution margin percentage, estimated net profit, and
payouts are **not implemented**. In particular, contribution excludes labor and
overhead and must never be called net profit. Deposits do not measure sales.
Collected sales taxes are not seller revenue. Production definitions and timing
must be agreed against statement samples before Phase 1 reconciliation.

Views, visits, conversion, customer demographics, and SEO search volumes are not
measured by the demo. No placeholder traffic data is generated.

## Statement source summaries (Phase 1 Part 1)

These are independent of demo KPIs and are not production revenue recognition.
Group accepted entries by source month and source category. Count source-row
occurrences, not orders or units. Sum each nullable signed monetary column
independently, with exact integer USD cents. A column with no supplied numeric
values remains unavailable rather than zero. Missing months are unavailable.

For nondeposits validate Net = Amount + Fees & Taxes, substituting zero for an
absent component only during the arithmetic check. Preserve absence in storage.
Deposits are extracted from a strictly recognized description into a separate
field and never treated as additional sales. Bill payments, buyer fees, taxes, shipping,
marketing and refunds remain separate categories. Positive fee/shipping values
are credits. Sale activity has not yet been decomposed into items, discounts,
shipping and tax; it must not be relabeled item revenue. No cross-category net
profit, AOV, contribution or tax-exclusive revenue is computed from these rows.

The UI displays the source Payment category as **Payment**, with the explanation
that these are payments toward the Etsy bill, not customer sales. The legacy
storage code `funding` is retained solely for compatibility.

## Fee breakdowns

Restrict to source Type Fee, then group by source month and the current versioned
fee subtype. Listing/processing/item transaction/shipping transaction/shop setup
have separate subtotals; unknown or not-yet-classified fees remain Unclassified.
Advertising and postage remain in their existing categories.

- Charges: sum of `-Net` for negative Fee Net values (positive cost magnitude).
- Credits: sum of `Net` for positive Fee Net values (positive offset magnitude).
- Net cost: charges minus credits, which may be negative for credit-only periods.

These are alternate breakdowns of the same source Fee entries. Never add the
breakdown to the aggregate Fee category again. Classifications without matching
source activity do not produce a financial total. Older annotation versions are
excluded from current reports, and fee rows without a current annotation remain
visible under Unclassified. Source dates and recorded amounts are preserved.
