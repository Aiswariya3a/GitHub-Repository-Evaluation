---
gsd_state_version: 1.0
milestone: v3.0
milestone_name: Executive AI Dashboard & Async Evaluation
status: completed
last_updated: "2026-07-18T13:45:00.000Z"
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 16
  completed_plans: 16
  percent: 100
---

# STATE.md

> Project memory for the multi-agent SLM evaluation pipeline.

---

## Project Reference

**Core Value:** Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

**Current Focus:** Milestones v1.0 + v2.0 + v3.0 complete — planning v4.0 (Human-in-the-Loop Review)

---

## Current Position

**Status:** v4.0 Phase 11 Complete (2026-07-18)

Milestones:

- ✅ v1.0 — SLM Pipeline Replacement (Phases 1-4, 12 plans)
- ✅ v2.0 — Frontend Dashboard (Phase 5, 4 plans)
- ✅ v3.0 — Executive AI Dashboard & Async Evaluation (Phases 6-10, 15 direct commits)
- 🔄 v4.0 — Human-in-the-Loop Review (Phase 11 complete, Phases 12-13 remaining)

**v4.0 Progress:** 6/6 plans complete (Phases 11-13 all complete)

**Next:** All v4.0 phases complete — ready for /gsd-complete-milestone

---

## Performance Metrics

| Metric | Value | Target | Notes |
|--------|-------|--------|-------|
| Total v1 requirements | 45 | 45 | ✓ Fully scoped |
| Total v3.0 features | 53 | 53 | ✓ Retroactively documented |
| Mapped to phases | 98 | 98 | ✓ 100% coverage (all milestones) |
| Phases defined | 10 | 10 | ✓ All completed |
| Plans created | 16 | — | Planned phases (1 v1.0 + 4 v2.0) |
| Plans completed | 16 | — | All planning-driven phases complete |
| Direct commits (v3.0) | 15 | — | Not formally planned, shipped directly |
| Tests created | 86 | — | 5 test files covering agents, schemas, aggregation, routing |

---

## Accumulated Context

### Decisions Made

| Decision | Rationale | Date |
|----------|-----------|------|
| 3-phase coarse structure | Granularity setting + natural delivery boundaries | 2026-07-06 |
| Phase 1 = Ingestion only | Foundation; no dependencies; agents need data | 2026-07-06 |
| Phase 2 = All agents + orchestrator + evaluation + Ollama | Tightly coupled pipeline; one delivery boundary | 2026-07-06 |
| Phase 3 = Cleanup + Testing | New pipeline must exist before removing old engine or testing it | 2026-07-06 |
| All 45 requirements mapped | No orphans; every requirement assigned to exactly one phase | 2026-07-06 |
| Phase 1 output = Project Snapshot JSON | Single hierarchical JSON per repo, rubric-agnostic, self-contained | 2026-07-06 |
| File discovery: extension + shebang | Configurable mapping, no hardcoded paths | 2026-07-06 |
| Parse: Python ast, regex for others | Built-in ast for Python; no tree-sitter v1 | 2026-07-06 |
| Delta: three-level hierarchical | Repo → file → symbol levels; symbol-level primary for agents | 2026-07-06 |
| Ingestion DB: JSONB in single table | Separated from evaluation schema; full snapshot + key columns | 2026-07-06 |
| OllamaClient uses raw HTTP (not Python SDK) | SLM JSON output instability requires direct HTTP control | 2026-07-07 |
| D-01: Agents are in-process Python classes with run() interface | Implemented via BaseAgent abstract class | 2026-07-07 |
| Temperature=0 enforced silently | All non-zero temps overridden with log warning for reproducibility | 2026-07-07 |
| 5 self-contained JSON Schema definitions (no $ref) | Direct use with jsonschema.validate() without external resolution | 2026-07-07 |
| D-03: Evidence routing via EVIDENCE_ROUTING_MAP | Category→section mapping in evidence_router.py with fuzzy matching | 2026-07-07 |
| D-05: Each criterion returns remarks (mini-feedback) | Implemented in RubricEvaluationAgent and CriterionEvaluation model | 2026-07-07 |
| D-08: Default max_parallel_agents=2 | Configurable; enforced by orchestrator ThreadPoolExecutor | 2026-07-07 |
| D-11: Idempotent file-based output | Each agent writes to output_path if provided; filesystem IS state | 2026-07-07 |
| Code agents → "code" model (Qwen2.5-Coder 3B) | RepoUnderstandingAgent + CodeUnderstandingAgent | 2026-07-07 |
| Collaboration/Evaluation → "reasoning" model (Phi-4 Mini) | CollaborationAgent + RubricEvaluationAgent per OLL-03 | 2026-07-07 |
| Evidence truncation at 8000 chars | Prevents context window overflow (Pitfall 2) | 2026-07-07 |
| Score aggregation is pure Python (no LLM) | aggregate_scores() uses round(), min(), max() only | 2026-07-07 |
| Missing criteria scored 0 with confidence_warning | Handles partial pipeline failures gracefully | 2026-07-07 |

| Orchestrator pipeline: 6 steps with file-based recovery | Idempotent step detection via output file existence; partial failure handling | 2026-07-12 |
| FeedbackAgent uses "reasoning" model (Phi-4 Mini) | Follows OLL-03 model routing for reasoning tasks | 2026-07-12 |
| Agent tests use mocked OllamaClient.infer() returning dict directly | Agents call with format="json", so mock returns parsed dict, not {"response": ...} | 2026-07-12 |
| _find_best_routing_key assumes lowercased input | route_evidence() lowercases before calling; internal function tests pass lowercased | 2026-07-12 |
| _filter_snapshot preserves '[]' in array wildcard keys | Routing map uses files[].functions notation; output dict uses 'files[]' as key | 2026-07-12 |
| Lazy import of generate_pdf inside report_service.generate() | Breaks circular dependency (pdf_gen -> services -> pdf_gen) | 2026-07-13 |
| Background threads for async evaluation | Simplest Flask approach; no Celery/RQ dependency | 2026-07-17 |
| progress_pct + current_step on repositories table | Avoids new progress table; sufficient granularity | 2026-07-17 |
| Dashboard: remove Action Center + Recent Sessions | Non-technical evaluators found them distracting | 2026-07-18 |
| Light mode via CSS custom properties + data-theme | Clean separation, no preprocessor, instant toggle | 2026-07-18 |
| Grade letter (A-F) on Overview | Faculty evaluators need at-a-glance scoring | 2026-07-17 |
| Code Quality → "AI Assessment Report" | Better terminology fit for faculty evaluators | 2026-07-17 |

### Open Questions

None — roadmap is ready for approval.

### Known Risks

- Phase 2 has 28 requirements (largest phase) — may need splitting into multiple plans during planning
- SLM JSON output stability requires validation + re-prompt logic (captured in ORC-03)
- Ollama model availability must be validated before pipeline runs (captured in OLL-04)
- Context window overflow possible with large repos — agent inputs should be minimal

### Blockers

None.

---

## Session Continuity

### Previous Sessions

- Initialized project structure
- Created PROJECT.md, REQUIREMENTS.md, config.json
- Ran research phase
- Created ROADMAP.md and STATE.md
- Discussed Phase 1 (Ingestion Pipeline) — context captured
- Planned and executed Phase 1 (3 plans) — ingestion pipeline complete
- Discussed Phase 2 (Evaluation Pipeline) — context captured
- Created Phase 2 plans (4 plans across 3 waves)
- **Executed Phase 2 Wave 1 (Plan 02-01)** — Foundation layer complete:
  - OllamaClient with model routing and connectivity validation
  - BaseAgent abstract class with run() contract
  - 5 JSON Schema definitions for all agent output types
  - Evaluation subpackage structure created
- **Executed Phase 2 Wave 2 (Plans 02-02 + 02-03)** — Capability Agents + Rubric Evaluation complete:
  - Plan 02-02: 3 capability extraction agents (Repo Understanding, Code Understanding, Collaboration)
  - Plan 02-03: Rubric evaluation engine (evidence routing, criterion evaluation, score aggregation)
  - All agents inherit from BaseAgent with schema validation and file-based output
- **Executed Phase 2 Wave 3 (Plan 02-04)** — Orchestrator, Feedback Agent, PostgreSQL persistence complete:
  - EvaluationOrchestrator: full 6-step pipeline lifecycle with parallel scheduling, retry, file-based recovery
  - FeedbackAgent: generates structured strengths/weaknesses/suggestions from aggregated scores
  - PipelineService: high-level entry point for controller integration
  - Migration 002: evaluation_results table with JSONB columns and indexes
  - All agents wire together: ingestion → capability → rubric → aggregation → feedback → persistence

### Previous Session

- **Executed Phase 5 Plan 3 (05-03)** — Plagiarism Results + JS Extraction + Analytics Enhancement complete:
  - Added plagiarism data + `has_low_confidence` boolean to session API response (4-tuple return from session_context())
  - Created `static/js/common.js` with shared utilities (esc, date, toast, confirmAction, statusTone, empty) on window.*
  - Created `static/js/session.js` with full session detail page logic including plagiarism tab renderer and low-confidence filter
  - Created `static/js/dashboard.js` with dashboard session listing, overview KPIs, and analytics page handlers (3 DOMContentLoaded blocks)
  - Created `static/js/reports.js` with reports listing logic
  - Extracted all inline JavaScript from 6 templates (base, session, dashboard, overview, reports, analytics)
  - Added plagiarism section to session page with similarity table
  - Added LowConfidence filter chip to session filter bar
  - Added score distribution histogram + session comparison table to analytics page
  - References to common.js loaded first; page-specific JS files use window.* utilities

### Previous Session

- **Executed Phase 5 Plan 2 (05-02)** — Ingestion Snapshot + Evaluation Detail Tabs complete:
  - Created `static/js/repository.js` with `renderIngestionTab()`, `renderEvaluationDetailTab()`, `renderCollaborationTab()` functions
  - Extracted all inline JS from `repository_detail.html` to external JS file
  - Added Ingestion and Evaluation Detail tab buttons and panels to template
  - Added low-confidence sidebar warning indicators
  - Added `.confidence-badge`, `.detail-row`, `.timeline-item`, `.score-bar` CSS classes to dashboard.css

### Previous Session (v4.0 Plan 11-01)

- **Executed Phase 11 Plan 1 (11-01)** — HITL Data Model & Backend: Database schema + Repository layer:
  - Added `review_queue`, `score_overrides`, `audit_log` tables to `database/schema.sql` with CHECK constraints, foreign keys, and 7 new indexes
  - Created `repositories/review_repository.py` with 3 repository classes (ReviewQueueRepository, ScoreOverrideRepository, AuditLogRepository) following existing psycopg/connect() pattern
  - All 3 classes exported from `repositories/__init__.py`
  - 3 atomic commits: schema (e10d791), repository classes (dc92c4b), exports (11a69d1)
  - Import verification passes

### Previous Session (v4.0 Plan 11-02)

- **Executed Phase 11 Plan 2 (11-02)** — HITL Review Service & API Endpoints:
  - Created `services/review_service.py` with ReviewService class (12 methods: auto_queue_repository, start_review, complete_review, list_queue, pending_count, get_queue_entry, override_score, get_overrides, get_audit_trail, evaluation_has_low_confidence, needs_review)
  - Created `controllers/review_controller.py` with 6 REST endpoints under `/api/reviews/` (list queue, review detail, start review, submit override, complete review, get audit trail)
  - Wired ReviewController in `controllers/__init__.py` and `app.py`
  - Added `reviews: ReviewService` to ServiceContainer dataclass with build() instantiation
  - Added `needs_review` boolean per repository row in `session_context()` alongside existing `has_low_confidence` flag
  - Added `pending_reviews` count to dashboard API response
  - Added auto-queue logic in `pipeline_service.py` — after successful evaluation, repositories with low-confidence criteria are auto-queued (best-effort, non-blocking)
  - 6 atomic commits: ReviewService (91be666), ReviewController (df50e52), registration (b195fc8), container (513375f), dashboard (b080e11), auto-queue (90bdabb)
  - Import verification passes

### Last Session (v3.0 Audit)

- **Retroactively documented v3.0 milestone** — all changes shipped as direct commits after v2.0 archive
- **15 commits audited** — 61 files changed, +5,411 lines added since v2.0
- **53 requirements documented** across 5 logical phases (6-10)
- **5 planning documents created/updated:** v3.0-REQUIREMENTS.md, v3.0-ROADMAP.md, PROJECT.md, ROADMAP.md, STATE.md
- **Dashboard redesign completed** as final v3.0 changes:
  - Fixed dashboard loading gatekeeper (`healthGauge` → `healthCard`)
  - Removed Action Center and Recent Sessions cards
  - Aligned dashboard font sizes with session tab sizing
- **Discovered v3.0 features:**
  - Collaboration analytics (equity waterfall, contributor profiles, network graph, health score)
  - Code Quality → AI Assessment Report redesign
  - Executive AI Dashboard Overview tab with grade letter
  - Async evaluation with background threads + real-time progress tracking
  - Settings page with `/api/system/status`
  - Light mode theme with localStorage persistence
  - Command palette (Ctrl+K), dynamic repo avatars, font size increase
  - Enhanced PDF reports (rubric-aware, per-repository)
  - Feedback Agent summary field with retry and fallback

### Previous Session (v4.0 Plan 11-02)

- **Executed Phase 11 Plan 2 (11-02)** — HITL Review Service & API Endpoints:
  - Created `services/review_service.py` with ReviewService class (12 methods)
  - Created `controllers/review_controller.py` with 6 REST endpoints under `/api/reviews/`
  - Wired ReviewController in `controllers/__init__.py` and `app.py`
  - Added `reviews: ReviewService` to ServiceContainer dataclass
  - Added `needs_review` boolean to session_context() response
  - Added `pending_reviews` count to dashboard API
  - Added auto-queue logic in pipeline_service.py

### Previous Session (v4.0 Plan 12-01)

- **Executed Phase 12 Plan 1 (12-01)** — Review Dashboard & Navigation UI:
  - Created Reviews nav link in sidebar and command palette
  - Added `/reviews` route in session_controller.py
  - Created `templates/reviews.html` with stats grid, toolbar, filter chips, data table
  - Created `static/js/reviews.js` with full review queue page logic (session filter, status filter, dual-mode loading, start review action)
  - Updated dashboard.js to show pending_reviews count
  - Added review badges to session page repo cards (needs_review flag)
  - 5 atomic commits

### Last Session (v4.0 Plan 12-02)

- **Executed Phase 12 Plan 2 (12-02)** — Review Panel & Score Override Controls:
  - Added Review tab button and panel to repository detail template
  - Created `static/js/review_detail.js` with full review panel logic (status hero, action buttons, score override inputs, submitted overrides, audit trail timeline)
  - Added review panel CSS classes to dashboard.css (review-hero, override-criteria, override-input, audit-timeline, etc.)
  - 3 atomic commits

### Last Session

- **Executed Phase 13 (13-01 + 13-02)** — Audit Trail, Badges & Roles:
  - Added green "Reviewed" badge to dashboard activity feed, leaderboard, and session repo cards
  - Fixed `/audit` route to render new `templates/audit.html` with filterable audit log table
  - Added "Audit Log" to sidebar navigation
  - Created SUMMARY.md for both plans
  - CSS classes for reviewed badges and performer display

### Next Session

- **v4.0 all phases complete** — run `/gsd-complete-milestone` to archive
- Next milestone planning (v5.0) if applicable

---

*Last updated: 2026-07-21 (Phase 13 complete)*
