# Unified sidebar navigation

The user selected Streamlit's built-in multipage navigation after reviewing
native navigation, automatic folder discovery and a custom sidebar selector.
The accepted layout is Statements (default), Import statements and Backups under
Shop, plus Synthetic demo under Examples. One main launch command opens all pages.

## Intent and scope

Make already imported real statements accessible from the main application and
provide a clear place for future capabilities. Split the existing statement app
into read-only saved reporting, confirmed uploads, and backup controls. Keep the
demo visibly synthetic and connected only to its existing separate settings.

Use `st.navigation`/`st.Page` with explicit registration in one module. This gives
control over groups, order, default page and URLs. Folder discovery is simpler
but less explicit about grouping; a custom selector duplicates routing/state
management. Native registration was selected by the user.

## Behavior and constraints

- `app/main.py` starts on Statements. The previous `app/statement_import.py`
  command remains a compatibility entry point opening Import statements with
  the same sidebar; it does not expose a second implementation.
- Statements shows existing coverage, import history, category/fee totals and
  source traceability. Initial coverage starts with the earliest imported month
  when present; missing/current-month caveats remain explicit. Other tables still
  represent all imported months, with no new revenue/profit calculations.
- Import statements retains validation, preview, confirmation, repeat-import
  and fee-classification behavior. Automatic backups remain in the write service.
  Navigating away from an unconfirmed upload does not accept it; returning requires
  reselecting/reviewing it under normal Streamlit widget lifecycle behavior.
- Backups contains existing manual backup and latest verification status.
- Synthetic demo retains its original metrics, warnings, settings and database.
  Missing/invalid real-data settings must not prevent selecting the demo page.
- Navigation or viewing does not import, classify, migrate, back up, or seed data.
  Existing `.env`, data paths, IDs, retention and privacy controls are unchanged.
- No dependency, schema migration, Etsy API/scope, deployment or live operation.
  Keep the current local feature branch; do not push before the user's testing.
  Preserve the user's uncommitted AGENTS.md edit.

## Implementation choices

File-based page scripts make native navigation testable with Streamlit AppTest.
Shared statement settings, database error handling and monetary formatting belong
in a small UI helper, while existing services remain responsible for business
behavior. Future pages require a script and one explicit registration entry.
Tests use synthetic fixtures and disposable databases, never the user's data.
