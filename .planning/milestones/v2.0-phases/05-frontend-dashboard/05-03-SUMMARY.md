---
phase: 05-frontend-dashboard
plan: 03
name: Plagiarism results, low-confidence filter, JS extraction, analytics enhancement
completed_date: 2026-07-13
duration: ~15 minutes
tasks_completed: 3/3
files_created:
  - static/js/common.js
  - static/js/reports.js
  - static/js/session.js
  - static/js/dashboard.js
files_modified:
  - controllers/common.py
  - controllers/session_controller.py
  - templates/base.html
  - templates/session.html
  - templates/dashboard.html
  - templates/overview.html
  - templates/reports.html
  - templates/analytics.html
subsystem: frontend-dashboard
tags: [js, css, templates, plagiarism, low-confidence, analytics, js-extraction]
requires: [05-02]
provides: [UI-03]
affects: [session_detail, dashboard, overview, reports, analytics, base_template]
tech-stack:
  added: []
  patterns:
    - "Shared JS utilities on window.* in common.js"
    - "DOMContentLoaded initialization inside closure (no globals except window.*)"
    - "4-tuple session_context() return with plagiarism data"
    - "Ternary batch low-confidence flag fetching per repo"
    - "innerHTML-based rendering (no framework)"
key-files:
  created:
    - path: "static/js/common.js"
      size: 1603 bytes
      purpose: "Shared utilities: window.esc, window.date, window.dateShort, window.when, window.toast, window.confirmAction, window.resolveConfirmation, window.statusTone, window.empty"
    - path: "static/js/reports.js"
      size: 1242 bytes
      purpose: "Reports page logic — fetch /api/sessions, filter by search, render report list with actions"
    - path: "static/js/session.js"
      size: 15173 bytes
      purpose: "Session detail page: card(), renderRepositories() with low-confidence filter, render() with plagiarism, renderPlagiarism(), load(), toggleSelection, evaluateOne, bulkEvaluate, evaluateAll, changeSessionStatus, deleteRepository, auto-refresh"
    - path: "static/js/dashboard.js"
      size: 11837 bytes
      purpose: "Dashboard page (session listing) + overview page (KPIs) + analytics page (score distribution + session comparison) — 3 DOMContentLoaded handlers"
  modified:
    - path: "controllers/common.py"
      purpose: "session_context() now fetches low_confidence flags per repo, fetches plagiarism data, returns 4-tuple"
    - path: "controllers/session_controller.py"
      purpose: "detail() and detail_api() destructure 4-tuple; detail() passes plagiarism to template; detail_api() includes plagiarism in jsonify"
    - path: "templates/base.html"
      purpose: "Links common.js in head; removes toast/confirmAction/resolveConfirmation from inline script (now in common.js); keeps command palette JS inline"
    - path: "templates/session.html"
      purpose: "Added plagiarism section with #plagiarismContent; added LowConfidence filter chip; replaced inline JS with session.js"
    - path: "templates/dashboard.html"
      purpose: "Replaced inline JS with dashboard.js"
    - path: "templates/overview.html"
      purpose: "Replaced inline JS with dashboard.js"
    - path: "templates/reports.html"
      purpose: "Replaced inline JS with reports.js"
    - path: "templates/analytics.html"
      purpose: "Added score distribution + session comparison sections; replaced inline JS with dashboard.js"
decisions:
  - "session_context() now returns 4-tuple (session, rows, summary, plagiarism) — existing callers updated"
  - "has_low_confidence fetched per-repo via container.repositories.evaluations.get_evaluation_result() (not container.evaluations which is PipelineService)"
  - "session.js no longer defines esc/date/confirmAction/toast locally — references window.* from common.js"
  - "dashboard.js contains 3 separate DOMContentLoaded handlers (dashboard, overview, analytics) — each guards with a DOM element check"
  - "Old inline scripts removed from 6 templates (base, session, dashboard, overview, reports, analytics)"
  - "Command palette JS (openCommandPalette, renderCommands, keyboard shortcut) remains inline in base.html because it directly references DOM elements"
metrics:
  duration_minutes: 15
  commits:
    - "100d345 — feat: add plagiarism + low_confidence to session API"
    - "522d947 — feat: create common.js + reports.js, extract inline JS from base/reports"
    - "ed669cb — feat: create session.js + dashboard.js, add plagiarism/low-confidence/analytics features"
---

# Phase 5 Plan 03: Plagiarism Results + Low-Confidence Filter + JS Extraction + Analytics Enhancement

Backend API now includes plagiarism data and per-repository `has_low_confidence` flags. Session detail page shows a plagiarism similarity table and a low-confidence filter chip. Analytics page has a score distribution histogram and a session comparison table. All inline JavaScript from the target templates has been extracted to dedicated `.js` files with shared utilities centralized in `common.js`.

## What was built

### 1. Backend API Changes (`controllers/common.py`, `controllers/session_controller.py`)
- `session_context()` now returns a **4-tuple**: `(session, rows, summary, plagiarism)`
- Each repository row now has a `has_low_confidence` boolean (fetched from `evaluation_results.low_confidence_criteria`)
- Plagiarism data is fetched via `container.repositories.plagiarism(session_id)` — returns list of `{roll1, roll2, similarity}` dicts
- `detail()` passes `plagiarism=plagiarism` to `render_template()`
- `detail_api()` includes `plagiarism=plagiarism` in the JSON response

### 2. `static/js/common.js` (48 lines) — Shared Utilities
- `window.esc()` — HTML escaping for all `innerHTML` rendering
- `window.date()` / `window.dateShort()` — localized date formatting
- `window.when()` — relative time ("5 minutes ago")
- `window.toast()` — toast notification system
- `window.confirmAction()` / `window.resolveConfirmation()` — modal confirmation dialog
- `window.statusTone()` — CSS class name for status badges
- `window.empty()` — empty state HTML template

### 3. `static/js/session.js` (378 lines) — Session Detail Page
- `card(r)` — repository card HTML builder with low-confidence warning strip
- `renderRepositories()` — filter/sort/paginate with new `LowConfidence` filter option
- `renderPlagiarism(plagiarism)` — renders similarity table into `#plagiarismContent`
- `render(d)` — full page render (stats, progress, insights, plagiarism, low-confidence chip count)
- All existing functions preserved: `load()`, `toggleSelection()`, `evaluateOne()`, `bulkEvaluate()`, `evaluateAll()`, `changeSessionStatus()`, `deleteRepository()`
- Auto-refresh every 5 seconds
- References shared utilities via `window.*`

### 4. `static/js/dashboard.js` (268 lines) — Dashboard + Overview + Analytics
- **Dashboard handler** (`#sessionDialog` guard): session listing with cards, search, create/delete sessions, rubric loading
- **Overview handler** (`#healthGauge` guard): KPI cards, health gauge, score chart, activity feed, running evaluations, technology breakdown, leaderboard
- **Analytics handler** (`#analyticsStats` guard): KPI stats, score distribution bars, session comparison table, completion bars

### 5. `static/js/reports.js` (33 lines) — Reports Page
- Fetches `/api/sessions`, filters to evaluated sessions, renders report list
- Search input filtering
- Uses `window.esc()` and `window.dateShort()` from common.js

### 6. Template Updates
| Template | Change |
|----------|--------|
| `base.html` | Added `common.js` script; removed `toast`/`confirmAction`/`resolveConfirmation` from inline JS (keeps command palette) |
| `session.html` | Added plagiarism section (`#plagiarismContent`); added LowConfidence filter chip; links `session.js` |
| `dashboard.html` | Links `dashboard.js` instead of inline script |
| `overview.html` | Links `dashboard.js` instead of inline script |
| `reports.html` | Links `reports.js` instead of inline script |
| `analytics.html` | Added score distribution + session comparison sections; links `dashboard.js` |

## Deviations from Plan

### Rule 3 - Blocking Issue Fix
**1. `container.evaluations.get_evaluation_result()` does not exist**
- **Found during:** Task 1 (has_low_confidence implementation)
- **Issue:** The plan's pseudo-code used `container.evaluations.get_evaluation_result(rid, sid)` but `container.evaluations` is `PipelineService` which doesn't have this method.
- **Fix:** Used `container.repositories.evaluations.get_evaluation_result(rid, sid)` instead — `RepositoryService.evaluations` is the `EvaluationRepository` which has the method.
- **Files modified:** `controllers/common.py`
- **Commit:** `ed669cb`

## Threat Surface Scan

| Threat ID | Category | Mitigation | Status |
|-----------|----------|------------|--------|
| T-05-03-01 | XSS via innerHTML | All user-facing data wrapped with `window.esc()` HTML-escaping | Implemented — common.js esc() used by all page JS files |
| T-05-03-02 | Plagiarism data in API | Accepted — data already queryable via RepositoryService | No change needed |

No new threat surface identified. Plagiarism data from the API is JSON only and goes through the same innerHTML + esc() rendering path.

## Verification Results

- ✅ `node --check static/js/common.js` — valid syntax
- ✅ `node --check static/js/reports.js` — valid syntax
- ✅ `node --check static/js/session.js` — valid syntax
- ✅ `node --check static/js/dashboard.js` — valid syntax
- ✅ `window.esc`, `window.toast`, `window.confirmAction`, `window.statusTone` in common.js
- ✅ `window.date`, `window.dateShort`, `window.when`, `window.empty` in common.js
- ✅ `base.html` links `common.js`; no `function toast` in inline script
- ✅ `session.html` links `session.js`; has `#plagiarismContent` section; has `data-status="LowConfidence"` filter chip
- ✅ `dashboard.html` links `dashboard.js`
- ✅ `overview.html` links `dashboard.js`
- ✅ `reports.html` links `reports.js`
- ✅ `analytics.html` has `#scoreDistribution` + `#sessionComparison` sections; links `dashboard.js`
- ✅ `common.py` has `container.repositories.plagiarism(session_id)` call (4 occurrences)
- ✅ `common.py` has `has_low_confidence` (4 occurrences)
- ✅ `session_controller.py` destructures 4-tuple in `detail()` and `detail_api()`
- ✅ `detail_api()` includes `plagiarism=plagiarism` in jsonify
- ✅ `DOMContentLoaded` in session.js — present (1 occurrence)
- ✅ `renderPlagiarism`/`plagiarismContent` in session.js — 4 occurrences
- ✅ `LowConfidence` in session.js — 2 occurrences
- ✅ `DOMContentLoaded` in dashboard.js — 3 occurrences (dashboard + overview + analytics)
- ✅ `td>` in dashboard.js — 1 occurrence (session comparison table, line 252)
- ✅ `openCommandPalette` preserved in base.html inline JS
- ✅ Minimum line counts: common.js (48≥40), session.js (378≥200), dashboard.js (268≥180), reports.js (33≥30)
- ✅ No file deletions in commits
- ✅ No untracked generated files

## Self-Check: PASSED

All created files exist, all commits verified, all acceptance criteria met.
