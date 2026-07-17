# Phase 5: Frontend Dashboard — Context

**Gathered:** 2026-07-13
**Status:** Ready for planning
**Source:** User request — "show nearly all useful data that we collected, and also produce the report correctly"

---

<domain>
## Phase Boundary

This phase delivers a polished frontend dashboard that surfaces all pipeline data (ingestion snapshots, agent evaluations, scores, evidence, feedback) and fixes the PDF report generation flow. The existing Flask + Jinja2 + vanilla JS frontend is extended with better data visualization, richer detail pages, and a reliable report pipeline.

**In scope:**
- Fix PDF report generation (currently broken subprocess-based flow)
- Surface ingestion snapshot data (file trees, language breakdown, repo metadata)
- Display agent evaluation results per criterion (evidence, confidence, remarks)
- Show collaboration analysis, code quality, documentation scores with detail
- Visualize low-confidence warnings and partial failures
- Cross-session analytics dashboard (trends, distributions, comparisons)
- Plagiarism detection results view
- Improve loading states, error handling, and UX polish

**Out of scope:**
- Authentication/OAuth (app assumes trusted network per PROJECT.md)
- Real-time streaming of evaluations (SSE/WebSocket)
- Mobile app or responsive redesign
- Major architectural changes to controllers/services
</domain>

<decisions>
## Implementation Decisions

### UI Approach
- **Stay with Jinja2 + vanilla JS** — no new frontend framework. The existing pattern is established and functional. Adding React/Vue would be disproportionate for this codebase.
- Extract inline JS into separate `.js` files for maintainability
- Consolidate `styles.css` and `dashboard.css` with section organization

### Report Generation (UI-01)
- **Fix pdf_gen.py subprocess flow** — currently `report_service.py` shells out to `pdf_gen.py`; PDF generation is fragile and failure-prone
- **Replace with direct Python API call** — refactor `pdf_gen.py` to expose a function that `report_service.py` imports directly, using the same core rendering logic but without subprocess
- Add proper error handling with meaningful messages displayed in the UI

### Data Display (UI-02 through UI-08)
- **Repository detail page:** Add ingestion snapshot tab showing file tree with language, size, and analysis results per file
- **Evaluation detail tab:** Show per-criterion results with evidence snippets, confidence indicators, and remarks
- **Collaboration tab:** Surface commit patterns, contributor stats, PR/issue data from GitHub metadata
- **Low-confidence filter:** Allow filtering repositories by confidence level across the session view
- **Plagiarism view:** Display plagiarism detection results in a table with similarity scores
- **Analytics page:** Add trend charts, score distribution histograms, session comparison view

### Code Organization
- Create `static/js/` directory and split current inline scripts into:
  - `dashboard.js` — overview page logic
  - `session.js` — session detail page
  - `repository.js` — repository detail page
  - `reports.js` — reports listing
  - `common.js` — shared utilities (toast, confirm, esc)
- Keep event binding pattern (no framework) — use DOMContentLoaded + event delegation

### CSS Architecture
- Keep two-file structure but organize with clear sections:
  - `styles.css` — base styles, typography, layout, navigation, components
  - `dashboard.css` — page-specific styles (moved from inline `<style>` blocks)
  - Remove any inline `<style>` tags from templates
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Templates (existing — modify)
- `templates/base.html` — Layout shell with nav, sidebar, dialogs, command palette
- `templates/overview.html` — Dashboard KPI overview with health gauge, score chart, activity feed
- `templates/dashboard.html` — Session listing with create dialog
- `templates/session.html` — Session detail with repository grid, filters, pagination
- `templates/repository_detail.html` — Repository-level view with tabs, score gauge, criterion cards
- `templates/reports.html` — Report listing page
- `templates/analytics.html` — Cross-session analytics
- `templates/settings.html` — Settings page
- `templates/rubrics.html` — Rubric listing
- `templates/rubric_detail.html` — Rubric detail/edit
- `templates/rubric_new.html` — New rubric form

### Controllers (API endpoints — read/verify)
- `controllers/session_controller.py` — Session CRUD, dashboard API, search
- `controllers/evaluation_controller.py` — Evaluation trigger endpoints
- `controllers/report_controller.py` — PDF report download endpoints
- `controllers/repository_controller.py` — Repository CRUD, detail API
- `controllers/rubric_controller.py` — Rubric CRUD, versioning

### Services (data layer — use for display)
- `services/repository_service.py` — Repository hydration, dashboard metrics, session insights
- `services/report_service.py` — PDF generation (NEEDS FIX)
- `services/github_service.py` — GitHub metadata fetching

### Models (data contracts)
- `models/evaluation_models.py` — CriterionEvaluation, CategoryScore, AggregatedScore
- `models/ingestion_models.py` — Ingestion snapshot structure
- `models/domain.py` — Base domain types

### Report Generation
- `pdf_gen.py` — PDF generation script (NEEDS REFACTOR — replace subprocess with direct API)
- `services/report_service.py` — Currently shells out to `pdf_gen.py` via subprocess.run
</canonical_refs>

<specifics>
## Specific Ideas

### Plan 5-01: Report Generation Fix
- Refactor `pdf_gen.py` to expose a `generate_pdf(session_id, output_dir)` function
- Update `report_service.py` to import and call directly instead of subprocess
- Add proper error messages displayed in the UI
- Test with existing evaluation data

### Plan 5-02: Repository Detail Enhancement
- Add ingestion snapshot tab showing file tree, language breakdown, analysis per file
- Add evaluation detail tab with per-criterion evidence, confidence, and remarks
- Add collaboration tab with contributor stats, PR/issue data
- Surface low-confidence warnings with visual indicators
- Extract inline JS to `static/js/repository.js`

### Plan 5-03: Session and Overview Improvements
- Add plagiarism results tab to session detail
- Add low-confidence repository filter
- Improve analytics page with trend charts and session comparison
- Extract inline JS to `static/js/session.js` and `static/js/dashboard.js`

### Plan 5-04: UX Polish
- Consolidate CSS files
- Improve loading states and error handling
- Ensure all API error responses display user-friendly messages
- Add keyboard navigation improvements
</specifics>

<deferred>
## Deferred Ideas

- Real-time evaluation progress via SSE/WebSocket — need would be confirmed by user
- Mobile-responsive design — app is web-only per PROJECT.md
- Dark mode theme — can be added later as a separate enhancement
- Export data as CSV/XLSX — out of scope for this phase
</deferred>

---

*Phase: 05-frontend-dashboard*
*Context gathered: 2026-07-13 via codebase analysis*
