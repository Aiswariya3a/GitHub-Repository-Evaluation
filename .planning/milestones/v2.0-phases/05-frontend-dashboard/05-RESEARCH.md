# Phase 5: Frontend Dashboard — Research

**Researched:** 2026-07-13
**Domain:** Flask frontend, Jinja2 templating, vanilla JS data visualization, PDF report generation
**Confidence:** HIGH

## Summary

Phase 5 delivers a polished frontend dashboard that surfaces all pipeline evaluation data and fixes the PDF report generation flow. The existing Flask + Jinja2 + vanilla JS frontend already has a solid foundation (dark-theme UI, gauge charts, tab-based navigation, search, skeleton loading states) but leaves significant pipeline data invisible to the user.

**The critical finding:** The evaluation pipeline collects rich per-criterion data (evidence snippets, confidence scores, remarks per criterion — stored in `evaluation_results.criterion_results` as JSONB), comprehensive ingestion snapshots (file-level analysis down to function/class granularity), and collaboration metadata (commit patterns, contributors, PRs/issues from GitHub). Almost none of this is surfaced in the current UI. The repository detail page only shows an overall score gauge, while session views only show repository cards with health scores.

**The primary technical challenge** is the broken PDF report pipeline. `report_service.py` shells out to `pdf_gen.py` via `subprocess.run()` — the script runs top-level code on import, instantiates its own services bypassing the DI container, and has no error handling. The fix is well-understood: refactor `pdf_gen.py` into callable functions, update `report_service.py` to import directly, and add proper error handling.

**Primary recommendation:** Refactor `pdf_gen.py` first (Plan 5-01), then build the data display features (Plans 5-02 through 5-04) using the existing API endpoints. The `repository_detail` API already returns ingestion data and evaluation results — the frontend just needs to render them. Every new display capability maps to data already available from existing endpoints; no new database queries or service methods are needed for Plans 5-02, 5-03.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### UI Approach
- **Stay with Jinja2 + vanilla JS** — no new frontend framework. The existing pattern is established and functional. Adding React/Vue would be disproportionate for this codebase.
- Extract inline JS into separate `.js` files for maintainability
- Consolidate `styles.css` and `dashboard.css` with section organization

#### Report Generation (UI-01)
- **Fix pdf_gen.py subprocess flow** — currently `report_service.py` shells out to `pdf_gen.py`; PDF generation is fragile and failure-prone
- **Replace with direct Python API call** — refactor `pdf_gen.py` to expose a function that `report_service.py` imports directly, using the same core rendering logic but without subprocess
- Add proper error handling with meaningful messages displayed in the UI

#### Data Display (UI-02 through UI-08)
- **Repository detail page:** Add ingestion snapshot tab showing file tree with language, size, and analysis results per file
- **Evaluation detail tab:** Show per-criterion results with evidence snippets, confidence indicators, and remarks
- **Collaboration tab:** Surface commit patterns, contributor stats, PR/issue data from GitHub metadata
- **Low-confidence filter:** Allow filtering repositories by confidence level across the session view
- **Plagiarism view:** Display plagiarism detection results in a table with similarity scores
- **Analytics page:** Add trend charts, score distribution histograms, session comparison view

#### Code Organization
- Create `static/js/` directory and split current inline scripts into:
  - `dashboard.js` — overview page logic
  - `session.js` — session detail page
  - `repository.js` — repository detail page
  - `reports.js` — reports listing
  - `common.js` — shared utilities (toast, confirm, esc)
- Keep event binding pattern (no framework) — use DOMContentLoaded + event delegation

#### CSS Architecture
- Keep two-file structure but organize with clear sections:
  - `styles.css` — base styles, typography, layout, navigation, components
  - `dashboard.css` — page-specific styles (moved from inline `<style>` blocks)
  - Remove any inline `<style>` tags from templates

### OpenCode's Discretion
*(None specified — all areas are locked decisions)*

### Deferred Ideas (OUT OF SCOPE)
- Real-time evaluation progress via SSE/WebSocket
- Mobile-responsive design
- Dark mode theme
- Export data as CSV/XLSX
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Fix PDF report generation (replace subprocess with direct API) | Verified: `pdf_gen.py` runs top-level code on import; `report_service.py` shells out via `subprocess.run`. Refactoring pattern established in research. |
| UI-02 | Add ingestion snapshot tab with file tree, language, size, analysis per file | Verified: `repository_detail` API already returns `repository.ingestion` with `files[]`, `repo_stats.language_breakdown`, and per-file `FileRecord` data. |
| UI-03 | Evaluation detail tab with per-criterion evidence, confidence, remarks | Verified: `repository_detail` API returns `repository.evaluation_result` with `criterion_results[]` containing `evidence[]`, `confidence`, `remarks`, `score`, `max_score`, `confidence_warning`. |
| UI-04 | Collaboration tab with commit patterns, contributor stats, PR/issue data | Verified: `repository_detail` API returns `repository.insights` with `commits`, `contributors`, `pull_requests`, `issues` from `related_data()`. Also `ingestion.github_metadata` contains aggregates. |
| UI-05 | Low-confidence repository filter | Verified: `evaluation_results.low_confidence_criteria` stored as JSONB. Current `session_context()` helper computes `normalized` but not low-confidence. Need to add this field to API response. |
| UI-06 | Plagiarism detection results view | Verified: `/api/sessions/<id>` returns session data. Plagiarism data stored in `plagiarism_results` table, fetched via `RepositoryService.plagiarism(session_id)` but NOT included in session API response. Need to add. |
| UI-07 | Analytics page with trend charts, score distribution, session comparison | Verified: `/api/dashboard` and `/api/sessions` endpoints provide all raw data needed. Current analytics page is thin — needs visualization of distributions, trends over time, session comparisons. |
| UI-08 | UX polish: loading states, error handling, loading states, keyboard nav | Verified: Base templates already have skeleton loading, toast, confirm dialog, command palette (Ctrl+K). Need to extract inline JS to `.js` files and consolidate CSS. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Ingestion snapshot display | Browser (client JS) | API (backend) | Data already returned by `/api/sessions/<sid>/repositories/<rid>` — frontend renders file tree and stats |
| Per-criterion evaluation display | Browser (client JS) | — | `criterion_results` array already in API response; frontend renders cards/tables with evidence/confidence/remarks |
| Collaboration metrics display | Browser (client JS) | API (backend) | `repository.insights` returns `commits`, `contributors`, `pull_requests`, `issues` from `related_data()` DB query |
| Low-confidence filtering | Browser (client JS) | — | Filter client-side on the `criterion_results` or `low_confidence_criteria` field already in evaluation_result |
| Plagiarism results view | Browser (client JS) | API (backend) | Need to add plagiarism data to session API response; frontend renders similarity table |
| Analytics charts | Browser (client JS) | API (backend) | `/api/dashboard` returns score distribution, technologies; `/api/sessions` returns per-session data |
| PDF report generation | Backend (service) | — | `report_service.py` + refactored `pdf_gen.py` — purely server-side; result served as file download |
| Report download trigger | API (controller) | Browser | `/sessions/<id>/report` endpoint already exists; just needs to work reliably after refactor |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask (Jinja2) | 3.x | Template rendering | Locked decision — existing framework; no framework change |
| CSS (vanilla) | — | Styling | Locked decision — two-file structure with section organization |
| Vanilla JS (ES2022) | — | Client interactivity | Locked decision — `DOMContentLoaded` + event delegation pattern |
| reportlab | 4.4.10 | PDF generation | Already the standard; used by `pdf_gen.py`. No alternative needed. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyPDF2 | 3.0.1 | PDF merging (report preamble + individual reports) | Report generation — merging step in `pdf_gen.py`. Should be preserved in refactor. |
| pandas | 3.0.1 | DataFrame operations for report aggregation | Report generation — used for score calculations and groupbys. Can be simplified or kept. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla JS rendering | Chart.js + D3.js | Locked decision: no new frontend frameworks. Visualizations stay CSS-based (progress bars, gauge rings, vertical bars). |
| reportlab | WeasyPrint / FPDF | Existing codebase already uses reportlab consistently. Refactoring to a new library would be disproportionate. |
| subprocess pdf_gen.py | Celery async task | Overkill — direct API call is sufficient for on-demand generation. Async queue is deferred per user decision. |

**Version verification:**
```bash
> reportlab: 4.4.10 [VERIFIED: pdf_gen.py imports]
> PyPDF2: 3.0.1 [VERIFIED: pdf_gen.py imports]
> pandas: 3.0.1 [VERIFIED: STACK.md + pdf_gen.py imports]
```

## Architecture Patterns

### System Architecture Diagram

```text
                            USER BROWSER
                                │
                    ┌───────────┼──────────────┐
                    ▼           ▼              ▼
            overview.html  session.html   repository_detail.html
            dashboard.html  analytics.html  reports.html
                    │           │              │
                    │  fetch JSON via fetch()  │
                    ▼           ▼              ▼
            ┌───────────────────────────────────────┐
            │         CONTROLLER LAYER               │
            │  session_controller  repository_ctrl   │
            │  report_controller   evaluation_ctrl   │
            └───────────┬───────────────────────────┘
                        │
            ┌───────────┼──────────────┐
            ▼           ▼              ▼
      SessionService  RepositoryService  PipelineService
      ReportService   RubricService      GitHubService
            │           │              │
            ▼           ▼              ▼
      ┌─────────────────────────────────────┐
      │        REPOSITORY LAYER              │
      │  SessionRepo  EvaluationRepo         │
      │  RepositoryRepo  IngestionRepo       │
      └──────────────────┬──────────────────┘
                         │
                         ▼
                   ┌──────────┐
                   │   PostgreSQL   │
                   └──────────┘

         PDF GENERATION PATH (after refactor):
         ReportController
              │
              ▼
         ReportService.generate()
              │  (direct import, no subprocess)
              ▼
         pdf_gen.generate_pdf(session_id, output_dir)
              │  reportlab + pandas + PyPDF2
              ▼
         Final_Consolidated_Report.pdf  
              │
              ▼
         send_file() → Browser download
```

### Recommended Project Structure
```
static/
├── js/
│   ├── common.js          # Shared utilities: toast, confirm, esc, date formatting
│   ├── dashboard.js       # Overview (dashboard) page logic
│   ├── session.js         # Session detail page logic
│   ├── repository.js      # Repository detail page logic
│   └── reports.js         # Reports listing page logic
├── styles.css             # Base styles, typography, layout, navigation, components
└── dashboard.css          # Page-specific component styles (organized by section)

templates/
├── base.html              # Layout shell (NO inline <style> tags)
├── overview.html          # Dashboard KPI overview (inline JS removed)
├── dashboard.html         # Session listing (inline JS removed)
├── session.html           # Session detail (inline JS removed)
├── repository_detail.html # Repository detail (inline JS removed)
├── reports.html           # Report listing (inline JS removed)
├── analytics.html         # Cross-session analytics (inline JS removed)
├── settings.html          # Settings (already clean)
├── rubrics.html           # Rubric listing
├── rubric_detail.html     # Rubric detail/edit
└── rubric_new.html        # New rubric form

pdf_gen.py                 # After refactor: exposes generate_pdf() function
services/report_service.py # After update: imports pdf_gen directly, no subprocess
```

### Pattern 1: DOMContentLoaded + Event Delegation
**What:** All page-specific JS initializes on `DOMContentLoaded`, using event delegation on static parent elements instead of direct event handlers on dynamic children.
**When to use:** Every page in the app — already the established pattern.
**Example:**
```javascript
// common.js — shared utilities
function toast(message, tone = 'success') { /* as in base.html */ }
function confirmAction(message, title = 'Confirm') { /* as in base.html */ }
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date = v => v ? new Intl.DateTimeFormat(undefined, {dateStyle:'medium', timeStyle:'short'}).format(new Date(v)) : 'Never';

// repository.js
document.addEventListener('DOMContentLoaded', () => {
    const page = document.getElementById('repositoryPage');
    if (!page) return;
    const sid = page.dataset.sessionId, rid = page.dataset.repositoryId;
    // ... load and render
});
```
**Source:** [VERIFIED: templates/base.html:28-36, templates/session.html:13-23, templates/repository_detail.html:7-11]

### Pattern 2: Skeleton Loading + API Fetch + Render
**What:** Pages render skeleton HTML on server, then fetch JSON from `/api/...` endpoints and replace skeletons with real content via `innerHTML`.
**When to use:** Every data-driven page (overview, session, repository detail, analytics, reports).
**Example:**
```html
<section class="stats-grid" id="sessionStats">
  {% for _ in range(4) %}
    <article class="metric-card skeleton-card">...</article>
  {% endfor %}
</section>
<script>
async function load() {
  const r = await fetch(`/api/sessions/${sid}`);
  const d = await r.json();
  if (!r.ok) throw Error(d.error);
  render(d);
}
</script>
```
**Source:** [VERIFIED: templates/session.html:5-6,13-19]

### Anti-Patterns to Avoid
- **Inline JS in templates:** The current code has all JS in `<script>` blocks inside HTML files. Locked decision requires extraction to `static/js/` files.
- **Subprocess PDF generation:** Currently shells out to `pdf_gen.py`. Locked decision requires direct API call instead.
- **Inline `<style>` tags:** None found in current templates (confirmed by grep), but the decision requires ensuring no new ones are added.
- **`eval()` or `new Function()`:** No occurrences found; the codebase uses safe patterns. Must keep it this way.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF generation | Custom report page writer | reportlab 4.4.10 | Already established in codebase; handles A4 layout, tables, styles, multi-page, images. Edge cases: page breaks, text overflow, table pagination. |
| PDF merging | Manual PDF concatenation | PyPDF2 3.0.1 (PdfMerger) | Already used in `pdf_gen.py:428-436`. Handles multi-document merging properly. |
| CSS framework | Custom component library | Keep existing two-file CSS | Decision to stay vanilla. Building a custom framework would be scope creep. |
| Chart library | SVG/Canvas chart from scratch | CSS-based charts (gauge rings, vertical bars, progress bars) | Current app uses CSS-only visualizations (conic-gradient gauges, vertical bar charts with CSS height, progress bars). Decision to stay vanilla. |
| Date formatting | Manual date parsing | `Intl.DateTimeFormat` + `Intl.RelativeTimeFormat` | Already used throughout the codebase (`overview.html:14`, `session.html:14`). Native browser APIs, no library needed. |

**Key insight:** The "Don't Hand-Roll" items are already established in the codebase. The danger is introducing new dependencies when the existing patterns are sufficient. Every visualization in the app can be done with CSS + vanilla JS using the patterns already proven in `overview.html` and `repository_detail.html`.

## Common Pitfalls

### Pitfall 1: Not respecting the two data paths for evaluations
**What goes wrong:** The repository detail API returns `evaluation_data.evaluation` (legacy hydrate format from old `evaluations` table) AND `evaluation_result` (new pipeline format from `evaluation_results` table). These have different structures — `evaluation` has `final.total_out_of_80` + `questions`, while `evaluation_result` has `criterion_results[]` + `feedback` + `low_confidence_criteria`.
**Why it happens:** The `_hydrate()` method in `repository_service.py:30-51` returns the legacy `evaluation` field, while `repository_detail()` adds the new `evaluation_result` separately (`repository_service.py:89-94`). The frontend currently reads from both (`repository_detail.html:9`: `e=r.evaluation_data.evaluation||{}` and `ev=r.evaluation_result||{}`).
**How to avoid:** Always use `evaluation_result` for the new pipeline data (which includes everything). The legacy `evaluation` field is a read-through from the old `evaluations` table — prefer the new format. Verify that `criterion_results` is non-empty before displaying.
**Warning signs:** Empty criterion arrays, zero scores despite "Completed" status.

### Pitfall 2: pdf_gen.py top-level code execution
**What goes wrong:** Running `import pdf_gen` or importing any function from it triggers the script's top-level code: argument parsing (`parser.parse_args()`), service instantiation (`RepositoryService()`, `SessionRepository().get()`), data loading, and PDF generation for the session.
**Why it happens:** The script was designed as a standalone CLI tool. Lines 59-64 run at module level, not inside a function. The current `report_service.py:21` uses subprocess to avoid this issue, but the locked decision requires direct import.
**How to avoid:** Wrap all module-level code (lines 59-440 except imports and utility definitions) in a `if __name__ == "__main__"` guard AND provide a `generate_pdf(session_id, output_dir)` entry function. The refactored file should have three layers: (1) utility functions, (2) `generate_pdf(session_id, output_dir)` that generates all reports, (3) `if __name__ == "__main__"` block for CLI usage.
**Warning signs:** `pdf_gen.py` currently fails when imported due to `parser.parse_args()` and `RepositoryService()` at module level.

### Pitfall 3: Template truncation of large data
**What goes wrong:** The inline JS in `repository_detail.html:9` has a line truncated at 2000 characters. The same risk applies when rendering large criterion results (dozens of criteria with evidence arrays).
**Why it happens:** The current templates pack all JS into single-line blocks inside `<script>` tags. As data grows, the line truncation limit in the Read tool is hit.
**How to avoid:** Extract JS to `.js` files where multi-line formatting is natural. For criterion rendering, use a loop that creates DOM elements (or appends to innerHTML) rather than building one giant HTML string.
**Warning signs:** Runtime errors where a constructor function string is truncated; missing data in rendered UI.

### Pitfall 4: Missing plagiarism data in session API response
**What goes wrong:** The session detail page cannot show plagiarism results because the session API (`/api/sessions/<id>`) does not include plagiarism data. The data exists in the `plagiarism_results` table and is queryable via `RepositoryService.plagiarism(session_id)`, but `session_context()` in `controllers/common.py` doesn't call it.
**Why it happens:** Plagiarism detection was added as a feature after the session API was built.
**How to avoid:** Add plagiarism data to the session API response in `session_controller.py:detail_api()` or in `session_context()` in `controllers/common.py`.
**Warning signs:** Empty plagiarism section on session detail page even when data exists.

### Pitfall 5: Low-confidence criteria not propagated to session-level
**What goes wrong:** The session API's repository list (from `session_context()`) computes `normalized` score but does not include `low_confidence_criteria` from `evaluation_results`. The session-level filter for low-confidence repos cannot work without this field.
**Why it happens:** `session_context()` in `controllers/common.py` iterates repositories and builds the response dict manually — it doesn't include `evaluation_result.low_confidence_criteria`.
**How to avoid:** Add a `low_confidence_criteria` field (or `has_low_confidence` boolean) to the session context helper. The data is already in the `evaluation_results` table's `low_confidence_criteria` JSONB column — just not exposed in the list API.
**Warning signs:** Zero-match filter results even when the admin knows some evaluations had low confidence.

## Code Examples

Verified patterns from codebase analysis:

### Report Generation Refactor Pattern

```python
# pdf_gen.py — refactored structure (target)

def generate_pdf(session_id: str, output_dir: str) -> str:
    """Generate full evaluation report for a session.
    
    Args:
        session_id: UUID of the evaluation session
        output_dir: Directory to write reports to
    
    Returns:
        Path to the merged Final_Consolidated_Report.pdf
    """
    # Data loading (moved from module level)
    store = RepositoryService()
    session_record = SessionRepository().get(session_id)
    saved_repos = [repo for repo in store.list_repositories(session_id) 
                   if repo["status"] == "Completed"]
    if not saved_repos:
        raise ValueError("No completed evaluations to report.")
    
    # Existing logic extracted from module-level code...
    # - resolve_rubric_snapshot()
    # - DataFrame construction
    # - Per-student PDF generation loop
    # - generate_preamble()
    # - merge_pdfs()
    
    return os.path.join(output_dir, "Final_Consolidated_Report.pdf")


def _make_student_report(roll, repo, evaluation, rubric_snapshot, styles, output_dir):
    """Generate individual student PDF. (extracted from the for loop)"""
    # ... existing reportlab logic ...


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    generate_pdf(args.session_id, os.getcwd())
```

### Services refactored to call pdf_gen directly

```python
# services/report_service.py — refactored

from __future__ import annotations
import tempfile
from pathlib import Path
from .repository_service import RepositoryService
from pdf_gen import generate_pdf  # Direct import instead of subprocess

class ReportService:
    def __init__(self, root: Path, repositories: RepositoryService):
        self.root, self.repositories = root, repositories

    def generate(self, session_id: str):
        repos = [repo for repo in self.repositories.list_repositories(session_id) 
                 if repo["status"] == "Completed"]
        if not repos:
            raise ValueError("This session has no saved evaluations to report.")
        temp = tempfile.TemporaryDirectory(prefix="evaluation-report-")
        directory = Path(temp.name)
        try:
            report_path = generate_pdf(session_id, str(directory))
            return temp, report_path
        except Exception as exc:
            temp.cleanup()
            raise RuntimeError(f"PDF generation failed: {exc}") from exc
```

### Rendering per-criterion evaluation with evidence

```javascript
// repository.js — criterion card with evidence and confidence

function renderCriterionResult(cr) {
    const conf = Number(cr.confidence || 0);
    const confClass = conf >= 0.7 ? 'high' : conf >= 0.5 ? 'medium' : 'low';
    const warnings = cr.confidence_warning || conf < 0.5 
        ? '<div class="warning-strip">! Low confidence — review manually</div>' 
        : '';
    const evidence = (cr.evidence || [])
        .map(e => `<li>${esc(e)}</li>`)
        .join('');
    
    return `
        <article class="metric-card ${cr.confidence_warning ? 'low-confidence' : ''}">
            <div class="metric-card-header">
                <span class="metric-orb"></span>
                <strong>${esc(cr.criterion_key)}</strong>
                <span class="confidence-badge ${confClass}">${(conf * 100).toFixed(0)}%</span>
            </div>
            <div class="score-bar">
                <span style="width:${Math.min(100, Number(cr.score) / Number(cr.max_score || 8) * 100)}%"></span>
                <span class="metric-score">${Number(cr.score).toFixed(1)} / ${Number(cr.max_score || 8).toFixed(0)}</span>
            </div>
            <p class="metric-remarks">${esc(cr.remarks || '')}</p>
            ${evidence ? `<details><summary>Evidence</summary><ul>${evidence}</ul></details>` : ''}
            ${warnings}
        </article>`;
}
```

### Adding plagiarism data to session API

```python
# controllers/common.py — session_context addition

def session_context(session_id):
    container = services(); session = container.sessions.get_session(session_id)
    if not session: abort(404)
    # ... existing rows processing ...
    
    # ADD: fetch plagiarism data for the session
    plagiarism = []
    try:
        plagiarism = container.repositories.plagiarism(session_id) or []
    except Exception:
        pass
    
    return session, rows, {
        "total": len(rows),
        "completed": sum(1 for r in rows if r["status"] == "Completed"),
        "pending": sum(1 for r in rows if r["status"] in {"Pending", "Failed"}),
        "average": round(average, 1),
        "public": sum(r["public"] for r in completed),
        "readme": sum(r["readme"] for r in completed),
    }, plagiarism  # <-- add fourth return value
```

### File tree rendering from ingestion snapshot

```javascript
// repository.js — file tree in ingestion tab

function renderFileTree(files, repoStats) {
    if (!files || !files.length) return '<div class="polished-empty">...</div>';
    
    const langBreak = repoStats?.language_breakdown || {};
    const langEntries = Object.entries(langBreak).map(([lang, count]) =>
        `<span class="topic-tag">${esc(lang)}: ${count} files</span>`
    ).join('');
    
    const langSummary = `<div class="repo-topics" style="margin-bottom: 16px">${langEntries}</div>`;
    
    const fileRows = files.map(f => {
        const loc = f.loc || f.code_loc || 0;
        const lang = esc(f.language || 'unknown');
        const path = esc(f.path);
        return `<div class="file-row">
            <span class="file-lang">${lang}</span>
            <span class="file-path">${path}</span>
            <span class="file-loc">${loc} lines</span>
        </div>`;
    }).join('');
    
    return langSummary + `<div class="file-list">${fileRows}</div>`;
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ALL templates: inline JS in `<script>` blocks | JS extracted to `static/js/*.js` files | This phase | Improved maintainability, code reuse, readability |
| `pdf_gen.py` standalone CLI script | `pdf_gen.py` exposes `generate_pdf()` function | This phase | Enables direct import without subprocess overhead |
| `report_service.py` uses `subprocess.run()` | `report_service.py` imports `pdf_gen.generate_pdf()` | This phase | Faster, more reliable, better error handling |
| No ingestion snapshot tab | Ingestion tab with file tree, language breakdown, per-file analysis | This phase | Surfaces existing data that was invisible |
| No per-criterion evidence view | Criterion cards with evidence, confidence, remarks | This phase | Surfaces rich LLM evaluation data |
| No plagiarism view | Plagiarism table with similarity scores | This phase | Surfaces existing plagiarism detection data |
| No low-confidence filter | Filter/label for repos with low-confidence criteria | This phase | Flags evaluations that need human review |

**Deprecated/outdated:**
- The legacy `evaluations` / `evaluation_questions` / `evaluation_criteria` tables coexist with the new `evaluation_results` table. The frontend should read from `evaluation_results` (via `repository_detail().evaluation_result`), not from `evaluation_data.evaluation` (which comes from legacy hydrate). For new features, always prefer `evaluation_result`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `repository_detail` API endpoint is called only when the repository detail page is visited — no existing page depends on it being fast or synchronous | Code Examples | Low — the current page already fetches it; the tab content is lazy-loaded by design |
| A2 | The plagiarism data is stored per-session in `plagiarism_results` table and can be fetched via `RepositoryService.plagiarism(session_id)` | Standard Stack | Low — verified the method exists in `repository_service.py:67` and SQL in `evaluation_repository.py:15-18` |
| A3 | Inline `<style>` tags in templates are confirmed absent by grep | Architecture Patterns | Low — confirmed by grep, but future additions should be prevented |
| A4 | The `session_context()` helper signature change to include plagiarism data won't break existing callers | Code Examples | MEDIUM — `session_context()` is called from `session_controller.detail()` and `detail_api()`. Both destructure the return as `session, repositories, summary = ...` — adding a fourth value won't break, but returning a dict change would. |

## Open Questions (RESOLVED)

1. **Does the plagiarism endpoint need a new API route or can it piggyback on existing session API?**
   - What we know: `RepositoryService.plagiarism(session_id)` returns data. Session API currently returns 3-tuple from `session_context()`. The session detail page (`session.html`) renders from the session API response.
   - What's unclear: Whether to add a separate `/api/sessions/<id>/plagiarism` endpoint (cleaner, on-demand) or include plagiarism data in the session API response (simpler, always loaded).
   - Recommendation: Include plagiarism in the session API response (add as fourth field in `session_context()`) — the data is small (≤ session repository count pairs) and avoids an extra HTTP round-trip.

2. **Should low-confidence filtering be done client-side or via a new API query parameter?**
   - What we know: `evaluation_results.low_confidence_criteria` is stored as JSONB. The session API returns all repositories with status but not the `low_confidence_criteria` field per repo.
   - What's unclear: Adding `low_confidence_criteria` to the session API response means every repo row includes a potentially large array of strings.
   - Recommendation: Use `has_low_confidence: boolean` in the session API response (add 1 field per repo), then filter client-side. If individual repo details are needed, the repository detail API already returns the full list.

3. **How to handle the analytics page charts?**
   - What we know: Current analytics page only shows session completion bars. `/api/dashboard` returns score distribution and technologies. `/api/sessions` returns per-session counts.
   - What's unclear: Whether to add time-series data (scores over time) which would require a new endpoint/query.
   - Recommendation: For this phase, use existing API data (dashboard metrics + session list) to build: (a) score distribution histogram (already in dashboard API), (b) technology breakdown (already in dashboard API), (c) per-session comparison table using session list data. Time-series analytics is a deferred idea.

## Validation Architecture

> Skipped — `workflow.nyquist_validation` is explicitly set to `false` in `.planning/config.json`. No test files are required for this phase's research scope.

## Security Domain

> Skipped — this phase touches no authentication, authorization, input validation, cryptography, or data-access control. It adds UI rendering of existing data and refactors internal report generation. No new security boundaries are introduced. All existing security assumptions (trusted network per PROJECT.md) remain unchanged.

## Sources

### Primary (HIGH confidence)
- **Codebase files** — All claims about existing code structure, API endpoints, data models, and template rendering verified by direct file reads and grep searches.
- **`pdf_gen.py`** (440 lines) — full read confirmed subprocess design, module-level code execution, reportlab usage, and merge logic.
- **`services/report_service.py`** (39 lines) — confirmed `subprocess.run()` call with `cwd=directory`.
- **`services/repository_service.py:repository_detail()`** (lines 74-99) — confirmed ingestion + evaluation_result + insights data in API response.
- **`models/evaluation_models.py`** (61 lines) — confirmed CriterionEvaluation, CategoryScore, AggregatedScore dataclass contracts.
- **`models/ingestion_models.py`** (148 lines) — confirmed ProjectSnapshot structure with FileRecord, GitHubMetadata, RepoStats.

### Secondary (MEDIUM confidence)
- **Cross-referenced template rendering** — Verified that existing JS in templates (`repository_detail.html:9`, `session.html:14-19`) reads both `evaluation_data.evaluation` (legacy) and `evaluation_result` (new pipeline).
- **Plagiarism data path** — Verified `RepositoryService.plagiarism()` → `EvaluationRepository.plagiarism()` → SQL query against `plagiarism_results` table. Confirmed NOT included in session API response.

### Tertiary (LOW confidence)
- None — all findings were verified against live codebase files.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — All libraries and versions verified directly from codebase files (imports, STACK.md, schema.sql).
- Architecture: **HIGH** — All data flow paths, API endpoints, and data models verified by reading source files.
- Pitfalls: **HIGH** — `pdf_gen.py` top-level code execution confirmed by reading line 59-64; session API missing plagiarism confirmed by reading `controllers/common.py:44-73`; low-confidence filter gap confirmed by grep of `low_confidence_criteria` in session context.

**Research date:** 2026-07-13
**Valid until:** 2026-08-13 (stable codebase — no fast-moving dependencies)
