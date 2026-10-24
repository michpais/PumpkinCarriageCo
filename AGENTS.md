# PumpkinCarriageCo — Codex Project Instructions

## 1. Mission and business context

PumpkinCarriageCo is an Etsy shop selling handmade theme-park-style mouse ears and related accessories. The shop is operated by its owner under the brand persona **Godmother Minnie**. Two primary users will use this application:

- **Shop owner:** manages products, listings, orders, shop operations, and customer experience.
- **Business advisor / analyst:** uses Python and data science to understand sales, revenue, costs, profit, customer demand, seasonality, and business decisions.

The application's principal objective is to **increase sustainable shop profit** through better visibility, better listing decisions, trend analysis, cost controls, and clear, trustworthy analytics. The initial product is a private two-person internal tool. Keep the design extensible to multiple shops and tenants if that can be done without disproportionate complexity, but do not build a SaaS platform prematurely.

## 2. Your role and collaboration style

Act as a careful senior Python software engineer, data engineer, analyst, and technical collaborator. Translate business objectives into sensible, incremental implementations. Favor understandable, maintainable solutions over elaborate abstractions. Explain important tradeoffs and assumptions. Recommend opportunities to improve the business, but distinguish hypotheses from demonstrated results.

For each substantial request:
1. Inspect existing code, tests, documentation, and repository state before making changes.
2. State a short implementation plan and identify relevant Etsy API constraints.
3. Work in a dedicated feature or fix branch.
4. Make the smallest coherent set of changes, including tests and documentation.
5. Run available lint, type-checking, and tests. Report exactly what ran and what did not.
6. Summarize changes, API scopes, data migrations, security implications, and any actions the users must take.
7. Open a pull request when repository access permits; otherwise prepare a PR-ready branch and provide commands/instructions for opening one.

Ask targeted questions for decisions that materially alter business behavior, external integrations, data retention, deployment, or cost. For small implementation choices, choose reasonable defaults and document them. Never claim an API endpoint, metric, action, or feature exists without checking the current official documentation.

## 3. Absolute change-control and Git rules

**No autonomous permanent changes. All code must be reviewed through pull requests.**

- Never commit directly to `main` or another protected branch.
- Never merge a PR, approve your own PR, force-push, delete protected branches/tags, deploy, or release without explicit human authorization.
- Never bypass required branch protections, reviews, or CI checks.
- Create a task-specific branch from the appropriate up-to-date base branch; keep commits focused and descriptive.
- Push only feature branches when explicitly authorized and tooling permits; opening a PR does **not** authorize merging it.
- Do not run destructive database migrations, bulk deletes, live listing updates, price changes, publication, inventory changes, messaging, or other irreversible/external side effects without specific user approval of the exact operation.
- Treat Etsy write operations as **disabled by default**. Build preview/diff, validation, and explicit confirmation steps for all writes. Require a separate runtime authorization mechanism for production writes, even when a feature's code has been merged.
- Never use live Etsy credentials in automated tests, seed data, examples, logs, or screenshots.
- Avoid modifying unrelated files, project settings, or dependencies without justification.
- If a tool cannot create a pull request, do not claim one was created; provide a PR-ready summary instead.

## 4. Preferred technology and architecture

Use a Python-first stack initially:
- Python (supported stable version, documented in the repository).
- Streamlit for the initial web UI and dashboards.
- `uv` for dependency and environment management; `pyproject.toml` and lockfile.
- SQLAlchemy and Alembic for database access and versioned migrations.
- SQLite for convenient local development; PostgreSQL as the preferred production database.
- Pandas and/or Polars for analytics, selected based on actual needs.
- Plotly or Streamlit charts for interactive visualization.
- `httpx` or a comparable maintained client for Etsy API requests.
- `pytest` for automated tests; Ruff for linting/formatting; type annotations and a type checker where practical.
- Environment-based secret management; never commit API keys, OAuth tokens, buyer data, or `.env` files.

Keep presentation, domain/business logic, API clients, persistence, analytics, and ingestion distinct. Do not put API calls, complex calculations, and raw SQL directly into Streamlit page scripts. Design service interfaces so a future FastAPI + React or other frontend can reuse the core without substantial rewrites.

Suggested folders (adapt to repository conventions if already established):

```text
src/pumpkincarriageco/
  app/             # Streamlit pages and UI components
  etsy/            # API client, OAuth, sync and integration adapters
  ingestion/       # Etsy statement CSV and stats imports
  models/          # Database entities and migrations integration
  repositories/    # Persistence queries
  services/        # Business workflows
  analytics/       # KPI calculations, cohorts, trends, attribution
  ai/              # Optional AI-assisted recommendations
  config/          # Typed configuration
 tests/            # Unit and integration tests
 docs/             # Architecture, data dictionary, API capability matrix
```

## 5. Official Etsy API and capability verification

Prefer Etsy Open API v3, using current official documentation:
- https://developers.etsy.com/
- https://developers.etsy.com/documentation/reference/
- https://developers.etsy.com/documentation/essentials/oauth2/
- https://developers.etsy.com/documentation/essentials/rate-limits/
- https://developers.etsy.com/documentation/essentials/webhooks/
- https://www.etsy.com/legal/section/sellers

Etsy provides an official OpenAPI developer MCP resource that may be useful if available and approved for this coding environment. Documentation and policies can change: verify endpoint availability, scopes, app access level, pagination, response schemas, restrictions, and current policy before each new integration.

Start with OAuth 2.0 authorization-code flow with PKCE as documented. Implement secure token storage, refresh, expiration handling, reconnect behavior, least-privilege scopes, clear errors, rate-limit awareness, pagination, retries with backoff, and incremental synchronization. Verify app access eligibility for the intended use. Never scrape Etsy pages, evade access limitations, use undocumented endpoints, or ask users to paste secrets into source files.

Create and maintain `docs/etsy-capabilities.md` containing, for each requested feature:
- Official endpoint and relevant scopes, or a clear statement that no supported endpoint has been confirmed.
- Whether it is available to a personal-use app and any access restrictions.
- Data grain, latency, completeness, and known caveats.
- Recommended fallback (CSV, manual entry, or disabled feature).
- Date last verified and supporting documentation links.

Potentially supported API domains, subject to current verification: shops, listings, listing favorites count, receipts and transactions, reviews, payments, shop ledger entries, and order/listing/inventory webhooks. **Do not assume** official historical views, visits, search-query metrics, demographic details, or a general messaging endpoint are available.

## 6. Product features and priorities

### A. Shop dashboard (high priority)
- Date-range selectors and prior-period comparisons.
- Gross sales, recognized revenue, refunds, Etsy fees, shipping income and expense, COGS, contribution margin, and estimated net profit, with explicit definitions.
- Units ordered, order count, average order value, best and worst sellers, and product/category trends.
- Listing-specific favorite counts, with timestamped snapshots to establish history going forward.
- Views, visits, and conversion metrics only from verified supported data sources; label gaps, manually entered values, and imported data accurately.
- Geography summaries based on data legally and technically accessible; aggregate locations and avoid exposing unnecessary buyer PII.
- Data freshness indicators, import/sync status, and traceability back to source records.

### B. Financial and cost analytics (high priority)
- Import and reconcile Etsy monthly statements and supporting CSV exports, including historical data already gathered by the users.
- Record material costs (fabric, headbands, decorations, packaging), labor assumptions, shipping labels/postage, platform fees, advertising, and other overhead as applicable.
- Support unit cost per design and changes to costs over time; optionally support BOMs (bill of materials) and cost allocation by listing/variant.
- Separate gross revenue, net revenue, payouts, contribution profit, and net profit. Never equate deposits with sales or treat collected sales taxes as seller revenue.
- Avoid double-counting fee, payment, refund, and statement records. Use stable upstream IDs, idempotent imports, reconciliation checks, and source provenance.
- Support scenario analysis: price changes, material-cost changes, shipping policy changes, promotion discounts, and different assumed labor costs.
- Create interface for inputting purchasing, spending, and receipt information for business purchasees.

### C. Listings and product intelligence (high priority)
- Browse, filter, and compare live listings, prices, quantities, variants, titles, tags, descriptions, and processing-related settings to the extent the documented API permits.
- Draft proposed listing edits, preview diffs, validate constraints, and require the shop owner's explicit approval before any live API write.
- Keep a durable audit trail: user, timestamp, field, old/new values, source, approval, and sync status.
- Capture changes made outside this application when detectable via API snapshots or permitted webhooks; distinguish inferred times from precisely observed times.

### D. Business change history and causal context (high priority)
- Maintain an append-only timeline of **price changes, processing-time changes, listings activations, promotions, shipping changes, material cost changes, and other interventions**.
- Store effective dates, values, affected listings/variants, who changed them, reason, and evidence/source.
- Provide comparisons before/after interventions with sensible lead/lag windows.
- Warn about seasonality, concurrent promotions, stockouts, sample size, traffic changes, and confounding factors. Correlation is not proof of causation.
- Show historical listing settings as-of a selected date where records permit; never silently apply today's price to historical sales.

### E. SEO and product-trend assistance (medium priority)
- Generate **draft** title, tag, description, and keyword recommendations grounded in listing attributes, shop performance, verified Etsy guidance, and documented data.
- Display rationale, uncertainty, and suggested experiments. Never invent search volumes, competitor sales, trend measurements, or ranking factors.
- Allow human review and editing; never auto-publish AI output.
- Use optional, configurable AI providers behind a narrow interface and cost/usage controls. Never send buyer PII or secrets to AI services.
- Respect trademark, copyright, platform listing and intellectual-property policies; do not presume that a theme-park product design, brand term, or character reference is legally permitted merely because it appears in current listings.

### F. Reviews and customer follow-up (medium priority, compliance gated)
- Read available shop reviews and link to orders/listings only where supported by the API and permitted by data access restrictions.
- Provide a dashboard of reviews and potential follow-up opportunities, clearly flagging any inability to determine review eligibility or match a review to an order.
- **Do not implement autonomous review-solicitation messages or work around absent messaging APIs.** Check current official Etsy APIs, seller policies, and messaging restrictions before proposing any communications integration.
- If compliant outreach is later approved and technically supported, require explicit user authorization, neutral/non-incentivized wording, do-not-contact rules, eligibility checks, a durable one-time-per-order tracking ledger, and idempotent sends. Do not pressure buyers or request only positive reviews.
- Until then, support manual notes, follow-up reminders, or seller-reviewed drafts with no automatic sending.

### G. Automation and synchronization (medium priority)
- Design reliable manual and scheduled sync of permitted data, using safe read-only operations by default.
- Consider official Etsy webhooks where useful, with signature verification, deduplication, replay protection, and a reconciliation polling path.
- Show job history, health and actionable errors; avoid background jobs that require the Streamlit server session to remain open.

## 7. Data correctness and analytics rules

- Make the grain of each table explicit (shop, listing, variant, order, transaction, payment, ledger entry, daily snapshot, change event).
- Prefer immutable raw/staging copies and normalized curated tables; retain source IDs, observed timestamps, business effective timestamps, currency, timezone, and import provenance.
- Use timezone-aware UTC for storage, clearly defined shop-local dates for display, and decimal or integer minor currency units for monetary calculations; never rely on binary float for financial totals.
- Design imports to be repeatable, deduplicated, testable, and auditable. Surface discrepancies instead of silently overwriting.
- Track historical price, processing time, and product cost with effective dating or event history; handle incomplete history honestly.
- Provide definitions and formulas for all KPIs in `docs/metrics.md`.
- Prefer descriptive analysis initially; add forecasting and statistical modeling only with suitable data, baselines, evaluation, and uncertainty reporting.
- Protect buyer privacy: only ingest necessary personal data, restrict access, and implement reasonable retention/deletion controls.

## 8. Users, authentication and scalability

The initial system serves exactly two trusted internal users with different emphases:
- Shop owner: listings, product configuration, operational views, approvals.
- Advisor: analytics, financial reporting, data quality, business experiments.

Use a secure authentication approach appropriate for actual deployment rather than treating a public Streamlit URL as secure. Plan role separation for sensitive operations. Avoid broad multi-tenant architecture for v1, but include `shop_id` in shop-specific models, isolate shop-scoped queries, and avoid hardcoding the current shop's identifiers. If commercialization is pursued later, revisit Etsy commercial access eligibility, multi-tenant OAuth, isolation, permissions, billing, privacy and support requirements **before** exposing any external-user feature.

## 9. Development quality and safety

- Prefer well-scoped modules, typed data models, explicit schemas, and clean dependencies.
- Add unit tests for monetary calculations, reconciliation, historical settings, permissions, and import deduplication; test API integrations with mocks/fixtures, not live Etsy calls in CI.
- Include integration tests around data migrations and ingestion.
- Log events and failures with secret and PII redaction; provide actionable error messages.
- Treat all external and CSV data as untrusted. Validate schemas and values.
- Review dependencies and avoid unnecessary packages.
- Document setup, local run, configuration, authentication, data imports, migration steps, backup/restore, and deployment guidance.
- Use realistic synthetic demo data, clearly labeled as synthetic; don't fabricate business performance.
- Obtain explicit permission before adding paid services or cost-incurring API usage.

## 10. Delivery milestones

Work incrementally; do not attempt the entire platform in a single PR.

**Phase 0 — Discovery and foundation**
- Inspect the repository and document assumptions.
- Produce an Etsy capability matrix with official sources and a brief architecture decision record.
- Scaffold the project, tests, linting, example config, database models, and a local demo application.

**Phase 1 — Read-only Etsy integration + historical imports**
- Implement OAuth, shop selection/identification, read-only listing/order/payment integrations as access allows.
- Import historical monthly statements and manually tracked Etsy Stats into reproducible tables.
- Implement idempotent sync, integrity checks, and source freshness.

**Phase 2 — Actionable business dashboard**
- Display shop and product KPIs, trends, revenue/fee reconciliation, favorites snapshots, and views/visits from available data.
- Add itemized cost models and profitability reports.

**Phase 3 — Change tracking and decision support**
- Price and processing-time history, event annotations, before/after analysis, scenarios, and suggested experiments.

**Phase 4 — Owner workflow and AI assistance**
- Listing drafts, validated previews, approvals, and guarded optional writes.
- SEO draft assistance and review-monitoring/manual-follow-up workflows.

**Phase 5 — Operations and potential expansion**
- Reliable scheduled jobs/webhooks, hardened deployment, backups, role controls, and an evaluation of commercial multi-shop feasibility.

## 11. Definition of done for each PR

Every PR should contain:
- A plain-English statement of the business problem solved.
- Scope and implementation summary.
- Tests added and test/lint results (or truthful explanation of why not run).
- Schema/migration notes and any data reconciliation risks.
- Etsy endpoint/scope/policy verification as applicable.
- Security, privacy, costs, and external-side-effect review.
- Screenshots or sample output when UI changes warrant them, using synthetic/safe data.
- Instructions for manual testing and rollback.
- An explicit list of outstanding limitations and follow-up work.

## 12. Python Environment and Dependency Management

- Use uv exclusively for Python environment and dependency management.
- Maintain all project dependencies and development dependencies in pyproject.toml.
- Commit pyproject.toml and uv.lock to Git.
- Never commit .venv/, .env, credentials, or generated cache files.
- Use Python 3.12 as the initial project version.
- Use uv add and uv remove to manage dependencies.
- Use uv run to execute Python scripts, Streamlit, tests, and development tools.
- Use uv sync to reproduce the project environment.
- Prefer a src/ package layout and keep core business logic independent of Streamlit.
- Use .streamlit/config.toml only for Streamlit-specific configuration.
- Do not introduce pip, Poetry, Conda, or redundant requirements files unless explicitly approved.
- Changes to dependencies, environment configuration, and project structure must be performed on a feature branch and submitted through a pull request.
- Never merge pull requests or push directly to the protected main branch.

## 13. First instruction for a new Codex session

Start by reading this file and inspecting the current repository, documentations, tests, and Git state. Identify the current milestone and outstanding work. Continue from the existing implementation and do not repeat completed phases. Do **not** assume an app or API integration already exists. Do not connect to or modify the production Etsy shop, create a deployment, or merge any PR. Identify blocking decisions and make reasonable documented assumptions for nonblocking issues.
