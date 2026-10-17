# Etsy Open API v3 capability matrix

Research date: **2026-10-16**. No credentials or live API requests were used.
Endpoint paths below are relative to `https://api.etsy.com/v3/application`.

## Verification sources and limits

The interactive [reference](https://developers.etsy.com/documentation/reference/)
returned a loading shell in one research tool. Exact operations, parameters,
security, and schemas were therefore checked against Etsy's public
[OpenAPI JSON](https://www.etsy.com/openapi/generated/oas/3.0.0.json), downloaded
on the research date (SHA256:
`BE4562B645FD6FA177B823C067037378C6E69CA2EEC1EA7D054654088AAD77C7`).
This is documentation verification, not proof of access for this unregistered app.
Recheck the live specification before implementing each adapter.

Current [app access guidance](https://developers.etsy.com/documentation/) describes
a Seller App path for eligible owners using their own shop and Personal Apps for
approved limited use beyond the developer's own shop. Personal App access is
reviewed and limited by the approved use case; do not assume a fixed shop allowance.
Commercial access is a later approval path. The owner-led Seller App appears the
best fit for this internal tool (recommendation, not a confirmed eligibility result).

In the matrix, **personal conditional** means the endpoint exists, but the app
must be approved for its use case and authorized shop/scopes. Seller App access is
restricted to its registered shop. Public data still requires an API key. Regional
or field-level restrictions can override endpoint availability. No latency or
historical-completeness SLA was established by this research.

## Features (each verified or explicitly unconfirmed on 2026-10-16)

| Requested feature | Official operation, path, OAuth scope | Access / grain / caveats | Fallback |
| --- | --- | --- | --- |
| Shop identity | [getShop](https://developers.etsy.com/documentation/reference/#operation/getShop), GET /shops/{shop_id}; no OAuth scope, API key | Public shop snapshot; personal conditional; use confirmed numeric ID, not a hardcoded shop | Manual configuration |
| Listing browse, titles, tags, description, current price/quantity | [getListingsByShop](https://developers.etsy.com/documentation/reference/#operation/getListingsByShop), GET /shops/{shop_id}/listings; listings_r | Personal conditional; listing grain; state filter; limit 1–100 (default 25), offset; current settings are not historical sales prices | Reviewed listing export/manual records |
| Variant inventory | [getListingInventory](https://developers.etsy.com/documentation/reference/#operation/getListingInventory), GET /listings/{listing_id}/inventory; listings_r | Personal conditional; listing → products/offerings, including variation data; current inventory does not reconstruct historical stockouts | Manual variant inventory |
| Favorite count | ShopListing.num_favorers on listing responses above | Personal conditional; current listing count only; record observed_at snapshots for future history; no historical favoriting timeline confirmed | Start snapshots after approved sync |
| Processing settings | [getShopReadinessStateDefinitions](https://developers.etsy.com/documentation/reference/#operation/getShopReadinessStateDefinitions), GET /shops/{shop_id}/readiness-state-definitions; shops_r; listings reference readiness_state_id | Personal conditional; processing profile grain, listing/variant applicability and nullable IDs need validation; legacy processing_min/max fields do not justify assuming complete current behavior | Manual effective-dated settings |
| Orders, refunds, shipping revenue | [getShopReceipts](https://developers.etsy.com/documentation/reference/#operation/getShopReceipts), GET /shops/{shop_id}/receipts; transactions_r | Personal conditional; receipt grain; created/last-modified bounds, status filters, limit/offset; paid vs unpaid must be explicit; totals, discounts, tax/VAT and refunds need reconciliation | Order and statement CSVs |
| Units, product sales and historical sold price | [getShopReceiptTransactionsByReceipt](https://developers.etsy.com/documentation/reference/#operation/getShopReceiptTransactionsByReceipt), GET /shops/{shop_id}/receipts/{receipt_id}/transactions; transactions_r; also GET /shops/{shop_id}/transactions | Personal conditional; transaction-line grain; transaction_id, listing_id, product_id, quantity, Money price, variations; receipt endpoint has no limit/offset parameters in checked spec, shop transaction endpoint does | Order item CSVs; never substitute today's price |
| Payments | [getPayments](https://developers.etsy.com/documentation/reference/#operation/getPayments), GET /shops/{shop_id}/payments; transactions_r | Personal conditional; payment grain; required payment_ids, not unrestricted paginated discovery; ledger linkage via GET /shops/{shop_id}/payment-account/ledger-entries/payments (ledger_entry_ids) | Payment/statement CSVs |
| Fees, cash movements, reconciliation | [getShopPaymentAccountLedgerEntries](https://developers.etsy.com/documentation/reference/#operation/getShopPaymentAccountLedgerEntries), GET /shops/{shop_id}/payment-account/ledger-entries; transactions_r | Personal conditional; ledger-entry grain; required min_created/max_created, limit/offset; do not sum receipt sales, payment totals and ledger credits as independent sales; deposits are not revenue | Monthly statement import and discrepancy report |
| Geography | Receipt country_iso and address fields via getShopReceipts; transactions_r | Personal conditional; receipt geography; spec warns address/city/state/zip/country access in some regions depends on preferred partnership; collect only permitted minimum, aggregate, suppress unnecessary PII | Aggregate manually or omit unavailable geography |
| Reviews | [getReviewsByShop](https://developers.etsy.com/documentation/reference/#operation/getReviewsByShop), GET /shops/{shop_id}/reviews; API key, no OAuth scope override | Public review grain; limit/offset and created bounds; ListingReview has shop/listing/rating/text/timestamps but no transaction_id; order matching and eligibility are not confirmed | Manual review notes; label unmatched reviews |
| Local business costs and purchases | No supported endpoint confirmed for material receipts, labor assumptions, BOMs, or other shop overhead | Local purchase/cost/effective-date grain; no Etsy scope supplies the business's full costs | Validated CSV/manual entry in future phase |
| Change history and interventions | Current listing/inventory snapshots plus permitted webhooks below; no complete past settings/event archive confirmed | Infer change intervals from observations; record local effective dates/reasons; promotion and shipping policy history must not be invented | Manual append-only timeline and evidence |
| Views, visits, conversion, search queries/volumes, demographics | No supported general historical metrics endpoint confirmed in checked spec | Do not infer from favorites, listings, or receipts; conversion requires traffic with compatible grain/period | Etsy Stats export/manual data labeled with source; otherwise unavailable |
| SEO recommendations | No verified search-volume, competitor-sales, or ranking-factor endpoint confirmed | Future local drafts may use listing facts and approved guidance; not evidence of measured demand | Human-reviewed experiments; no generated performance claims |
| Messaging and review solicitation | No supported general messaging endpoint confirmed; review eligibility endpoint not confirmed | Disabled; absence of API cannot be bypassed by scraping or browser sending | Manual notes/reminders or seller-reviewed drafts only |
| Listing drafts and future writes | [updateListing](https://developers.etsy.com/documentation/reference/#operation/updateListing), PATCH /shops/{shop_id}/listings/{listing_id}; listings_w | Personal conditional, owner authorization; exact field validation and inventory/profile endpoints require re-verification; activation may publish/renew, with fees | Local draft/diff only; no write adapter in Phase 0/1 |

## Authentication and request constraints

The current [authentication guide](https://developers.etsy.com/documentation/essentials/authentication/)
requires an API key plus OAuth on scoped endpoints. Use authorization-code PKCE
(S256), unpredictable single-use state, exact registered HTTPS redirect matching,
and server-side secret handling. Access tokens expire; refresh and reconnect must
be implemented and tested. Request only the read scopes each enabled feature needs.
No OAuth scopes are requested by this Phase 0 application.

[Request standards](https://developers.etsy.com/documentation/essentials/requests/)
currently specify `x-api-key` as keystring + colon + shared secret. Both are secret
configuration, never browser-visible or logged. Money uses amount/divisor/currency;
validate the divisor and retain exact values. Read response schemas per operation,
not only guide examples. The current personalization migration also means old
flat fields cannot be assumed; see the
[migration guide](https://developers.etsy.com/documentation/tutorials/personalization-migration/).

Pagination is endpoint-specific. Listings, receipts, reviews, and ledger collections
use limit/offset (usually default 25, max 100); payments use required ID lists;
inventory is a nested document. Inspect count/results and termination carefully.
Offset paging can drift during changes: Phase 1 should use bounded time windows,
overlap, source-ID deduplication, and reconciliation before advancing a cursor.

[Rate limits](https://developers.etsy.com/documentation/essentials/rate-limits/)
are application-key QPS and rolling-24-hour QPD quotas. Read actual portal/header
values; examples are not entitlements. Handle 429 and retry-after, bounded
exponential backoff with jitter, and actionable errors. Do not retry permanent
authorization/validation failures blindly. No polling frequency is promised yet.

## Webhooks and policy gates

The [webhook guide](https://developers.etsy.com/documentation/essentials/webhooks/)
now documents availability for approved personal and commercial applications.
Order events cover paid/canceled/shipped/delivered; listing events cover
created/updated/deleted; inventory events additionally include out_of_stock.
Listing update events cover a defined subset of fields; inventory updates include
price/readiness/SKU/state. Notifications do not establish a full history or remove
the need for API reconciliation. Confirm Seller App portal availability separately.

Before implementation: approve a public callback, verify HMAC against raw bytes,
validate timestamps and resource hosts, deduplicate webhook-id, persist a queue,
and reconcile through authorized read endpoints. Webhooks are deferred; no endpoint
or subscription was created.

[Seller policy](https://www.etsy.com/legal/sellers/) and
[API terms](https://www.etsy.com/legal/api/) remain gates for communications,
caching/retention, buyer privacy, IP, and future writes. No communications
integration is approved here; no design or trademark use is declared legally
permitted. Review policies again against the exact proposed workflow.
