# Unified Sidebar Navigation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline for this single
> cohesive task. Steps use checkbox syntax to track the test-first implementation.

**Goal:** Open the real statement views and existing workflows through one native sidebar.

**Architecture:** A small navigation module registers four file-based Streamlit
pages. Shared statement UI helpers keep configuration, formatting and safe database
errors consistent; source ingestion, persistence, backup and demo services stay unchanged.

**Tech Stack:** Existing Python 3.12, Streamlit, SQLAlchemy, pytest/AppTest, uv.

**Spec:** `docs/superpowers/specs/2026-10-24-sidebar-navigation-design.md`.

## Global constraints

- Main defaults to Statements; legacy statement entry point defaults to Imports.
- Shop pages use statement settings; Synthetic demo uses demo settings only.
- No database migration, source-file change, import or backup merely from viewing.
- No dependencies, Etsy connection, live writes, push, merge or deployment.
- Continue on `codex/phase-1-statement-import`; preserve the user's AGENTS.md edit.

## Review focus

- Native page switches really execute the selected file and leave data unchanged.
- Broken/missing real configuration still permits navigation to the separate demo.
- Confirmed imports/classification still pass through the required backup gate.
- Upload confirmation does not survive navigation as a silently authorized write.
- Coverage stays numeric/null, distinguishes empty/missing months and emits no Arrow fallback.

## Task 1: Native navigation and page split

**Files:** Create `app/navigation.py`, `app/statement_ui.py`, and scripts under
`app/views/` for statements, imports, backups and demo. Replace the two entry
scripts with thin calls to navigation. Update `tests/test_app.py` and
`tests/test_statement_app.py`; add `tests/test_navigation.py`. Update README,
operations, architecture and the Part 1 PR summary with launch/extension guidance.
All app paths are under `src/pumpkincarriageco/`.

**Interfaces:** `run_app(default_page: Literal['statements', 'imports'] = 'statements')`
registers pages and runs the selected one. Shared helpers load statement settings,
yield a checked/disposed engine, and format exact-money display tables. Pages call
existing services; no service signatures or data models need changing.

- [x] Write failing navigation tests: main renders saved Statement data without
  demo metrics or upload/backup controls; switching to registered Imports/Backups
  isolates controls; demo remains available with missing real settings; no records
  or backup files are created by navigation.
- [x] Run `uv run pytest tests/test_navigation.py -q` and observe the failure.
- [x] Split existing UI into the four pages and shared helpers, add native page
  registration, and retain the legacy upload launch command.
- [x] Adapt existing UI tests to switch through registered pages. Keep coverage,
  privacy, imports, credits, repeat import, confirmation and backup failure checks.
  Add a navigation-away test proving unconfirmed selections do not write data.
- [x] Run `uv run pytest`, Ruff lint/format and mypy; inspect every result.
- [x] Document launch command, sidebar purpose, extension example, no migration,
  existing settings and no new financial metrics. Review only this task's diff
  from baseline `7191295` plus its interactions with existing services.
- [x] Obtain one fresh read-only code review, address material findings with
  regression tests, then save one focused local commit and report how to test.

## Execution record

The user approved the proposed pages and selected native navigation. Continue in
the same feature checkout so their existing local launch/settings remain usable;
no new checkout or worktree is needed for this continuation. Implementation is
inline because this is one tightly coupled UI refactor. The existing uncommitted
AGENTS.md change belongs to the user and is outside this commit.

Navigation tests failed before implementation and passed after the page split.
The final full suite passed: 79 tests; mypy checked 30 source files successfully.
Ruff lint passed. The format check caught a trailing comma in the README's Python
example; the example was corrected before the final format check.

The independent source review found no critical or important issues. It flagged
the missing Payment explanation on Imports as minor. This was treated as a
preservation regression because the earlier labeling change distinguished Etsy
bill payments from customer sales. An assertion in the existing UI test failed
before restoring the caption, then the complete suite passed with it restored.
No browser visual inspection or real file-picker test was performed; automated
Streamlit AppTest covers routing, saved reports, confirmation and write guards
with synthetic temporary databases. Real databases and OneDrive files were untouched.
