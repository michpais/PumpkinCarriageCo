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
