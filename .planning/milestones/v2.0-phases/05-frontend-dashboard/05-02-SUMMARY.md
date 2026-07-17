---
phase: 05-frontend-dashboard
plan: 02
name: Ingestion snapshot + evaluation detail tabs
completed_date: 2026-07-13
duration: ~6 minutes
tasks_completed: 2/2
files_created:
  - static/js/repository.js
files_modified:
  - static/dashboard.css
  - templates/repository_detail.html
subsystem: frontend-dashboard
tags: [js, css, templates, tabs, ingestion, evaluation, collaboration, low-confidence]
requires: []
provides: [UI-02]
affects: [repository_detail, dashboard_css]
tech-stack:
  added: []
  patterns:
    - "DOMContentLoaded initialization + event delegation"
    - "innerHTML-based rendering (no framework)"
    - "Skeleton loading → async fetch → render"
key-files:
  created:
    - path: "static/js/repository.js"
      size: 21166 bytes
      purpose: "All repository detail page JavaScript — ingestion tab, evaluation detail tab, collaboration tab, low-confidence indicators, preserved render/load/runEvaluation functions"
  modified:
    - path: "static/dashboard.css"
      purpose: "Added .confidence-badge, .detail-row, .timeline-item, .score-bar, .metric-card-header, .metric-remarks, .ingestion-content classes"
    - path: "templates/repository_detail.html"
      purpose: "Replaced inline JS with external script src, added Ingestion/Evaluation Detail tab buttons and panels"
decisions:
  - "renderCollaborationTab() only overrides gm-based content when insights from related_data() are available — otherwise preserves existing rendering"
  - "renderEvaluationDetailTab() groups criteria by category_code with section headers and category totals"
  - "Low-confidence sidebar indicator appends warning-strip to scoreMeta when low_confidence_criteria is non-empty"
  - "CSS classes added in minified format matching existing dashboard.css style"
metrics:
  duration_minutes: 6
  commits:
    - "4f3d628 — create repository.js with ingestion, evaluation, collaboration, low-confidence renderers"
    - "e35a632 — add ingestion and evaluation detail tabs to repository_detail.html"
---

# Phase 5 Plan 02: Ingestion Snapshot + Evaluation Detail Tabs

Extracted inline JavaScript from `repository_detail.html` into `static/js/repository.js` and added three new tab renderers (Ingestion, Evaluation Detail, Collaboration) to surface pipeline data that was previously invisible in the UI.

## What was built

### 1. `static/js/repository.js` (21KB, 322 lines)
- **DOMContentLoaded** initialization pattern — all functions defined inside closure, no globals
- **Shared utilities** — `esc()`, `empty()`, `criterionCard()` preserved exactly from existing code
- **`renderIngestionTab(ingestion)`** — renders file tree with language breakdown badges, per-file LOC, path info into `#ingestionContent`
- **`renderEvaluationDetailTab(evaluationResult)`** — groups `criterion_results[]` by `category_code`, renders per-criterion cards with:
  - Score bar (width proportional to `score/max_score`)
  - Confidence badge (green ≥ 0.7, amber ≥ 0.5, red < 0.5)
  - Remarks text (HTML-escaped)
  - Expandable evidence section (`<details><summary>`)
  - Warning strip if `confidence_warning` is true or confidence < 0.5
- **`renderCollaborationTab(insights)`** — enriches collaboration tab with data from `related_data()`, showing:
  - Contributor rows with contribution counts
  - Commit timeline (author, message, date)
  - KPI cards for commits, PRs, issues, contributors
- **Low-confidence sidebar** — appends warning strip to `scoreMeta` when `low_confidence_criteria[]` is non-empty
- **Preserved** `render()`, `load()`, `runEvaluation()` functions with new tab renderer calls added
- **Tab switching** via event delegation on `repositoryTabs`

### 2. `templates/repository_detail.html`
- Added **Ingestion** tab button → `<section id="tab-ingestion">` with skeleton block
- Added **Evaluation Detail** tab button → `<section id="tab-evaluation">` with skeleton block
- Replaced inline `<script>` block with `<script src="{{ url_for('static', filename='js/repository.js') }}">`
- All 6 existing tabs (overview through history) preserved unchanged

### 3. CSS additions to `static/dashboard.css`
- `.confidence-badge` and `.high`/`.medium`/`.low` variants — pill badges for confidence levels
- `.detail-row` — flex row for contributor stats
- `.timeline-item` — commit timeline event row
- `.score-bar` — criterion score visualization
- `.metric-card-header`, `.metric-remarks` — card layout refinements
- `.metric-card.low-confidence` — red-tinted border for low-confidence criteria
- `.ingestion-content` — min-height container

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new threat surface identified. All data rendered via JS `innerHTML` is already HTML-escaped via the `esc()` utility. No new API endpoints or auth paths were introduced.

## Verification Results

- `node --check static/js/repository.js` — **PASS** (valid JS syntax)
- `renderIngestionTab` function — present ✓
- `renderEvaluationDetailTab` function — present ✓
- `renderCollaborationTab` function — present ✓
- `confidence_warning` handling — present ✓
- `esc()` HTML escaping utility — present ✓
- `category_code` grouping — present ✓
- `DOMContentLoaded` initialization — present ✓
- No `criterion_card` (old naming) — present ✓ (0 occurrences)
- Template has `<script src="{{ url_for('static', filename='js/repository.js') }}">` — ✓
- Template has no inline JS block — ✓
- All 6 existing tabs preserved — ✓

## Self-Check: PASSED

All created files exist, all commits verified, all acceptance criteria met.
