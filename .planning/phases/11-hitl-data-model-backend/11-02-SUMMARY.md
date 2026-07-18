---
phase: 11-hitl-data-model-backend
plan: 02
subsystem: api
tags: [flask, review, hitl, service, api, integration]
requires:
  - phase: 11-hitl-data-model-backend
    plan: 01
    provides: review_queue, score_overrides, audit_log database tables and repositories
provides:
  - ReviewService orchestrating queue management, score overrides, and audit trail
  - REST API endpoints under /api/reviews/ for all review operations
  - Auto-queue integration on evaluation completion for low-confidence repositories
  - Dashboard integration with pending_reviews count and per-repo needs_review flag
affects: [frontend, ui-phase]
tech-stack:
  added: []
  patterns:
    - Service class delegating to multiple repositories (ReviewService → ReviewQueueRepository, ScoreOverrideRepository, AuditLogRepository, EvaluationRepository)
    - Flask Blueprint controller registered via ServiceContainer
    - Best-effort auto-queue with try/except on evaluation completion
key-files:
  created:
    - services/review_service.py
    - controllers/review_controller.py
  modified:
    - controllers/__init__.py
    - app.py
    - services/container.py
    - controllers/common.py
    - controllers/session_controller.py
    - services/evaluation/pipeline_service.py
key-decisions:
  - "needs_review computed inline in session_context() using container.reviews.needs_review() with same try/except pattern as has_low_confidence"
  - "Auto-queue wrappped in try/except to ensure evaluation completion is never blocked by queue logic"
  - "ReviewService lazily uses ReviewQueueRepository/SccoreOverrideRepository/AuditLogRepository/EvaluationRepository instances (default constructor)"
requirements-completed: [ReviewService, API endpoints, Auto-queue on evaluation, Dashboard integration]
---

# Phase 11 Plan 02: HITL Review Service & API Endpoints

**ReviewService orchestrator with 6 REST endpoints under /api/reviews/, auto-queue on evaluation completion, and needs_review/pending_reviews dashboard flags**

## Performance

- **Duration:** 2m 36s
- **Started:** 2026-07-18T13:08:06Z
- **Completed:** 2026-07-18T13:10:42Z
- **Tasks:** 5
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments
- ReviewService with queue management (auto-queue, start_review, complete_review, list_queue, pending_count, get_queue_entry)
- Score override support with original score extraction from evaluation_results and full audit trail
- 6 REST API endpoints under /api/reviews/ including list, detail, start, override, complete, and audit
- ReviewController registered via ServiceContainer in controllers/__init__.py and app.py
- ReviewService wired into ServiceContainer dataclass alongside existing services
- session_context() surfaces needs_review boolean per repository row
- Dashboard API returns pending_reviews count aggregated across all sessions
- Auto-queue on evaluation completion for low-confidence repositories (best-effort, non-blocking)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ReviewService** - `91be666` (feat)
2. **Task 2: Create ReviewController** - `df50e52` (feat)
3. **Task 3: Register ReviewController** - `b195fc8` (feat)
4. **Task 3b: Add ReviewService to ServiceContainer** - `513375f` (feat)
5. **Task 4: Update session_context and dashboard** - `b080e11` (feat)
6. **Task 5: Auto-queue on evaluation completion** - `90bdabb` (feat)

**Plan metadata:** _(pending final commit)_

## Files Created/Modified

### Created
- `services/review_service.py` - ReviewService class with 12 methods for review queue management, score overrides, audit trail, and helper queries
- `controllers/review_controller.py` - Flask Blueprint with 6 GET/POST endpoints under /api/reviews/

### Modified
- `controllers/__init__.py` - Added ReviewController import and __all__ registration
- `app.py` - Added ReviewController import and blueprint registration
- `services/container.py` - Added ReviewService import, field, and build() instantiation
- `controllers/common.py` - Added needs_review flag in session_context() alongside existing has_low_confidence logic
- `controllers/session_controller.py` - Added pending_reviews to dashboard_api() response
- `services/evaluation/pipeline_service.py` - Added auto_queue_repository() call after successful evaluation

## Decisions Made

- **needs_review in session_context():** Added within the same try/except block as has_low_confidence, using the existing per-row iteration pattern. If the container or ReviewService is unavailable, needs_review defaults to False.
- **Auto-queue pattern:** Follows best-effort principle — wrapped in try/except to ensure that queue failures never block or interrupt evaluation completion.
- **ReviewService instantiation in pipeline:** Uses `ReviewService()` with no arguments (all repository defaults) rather than injecting via container, keeping the integration lightweight and avoiding circular dependencies.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data paths are fully wired.

## Threat Flags

None — all new API endpoints follow existing patterns with no unexpected trust boundary changes.

## Issues Encountered

None.

## Next Phase Readiness

- ReviewService and API endpoints are ready for frontend integration (phase 11-ui)
- All review operations are fully functional via REST API
- Queue entries are auto-populated on evaluation completion
- Dashboard and session_context() surface review flags to the UI layer

## Self-Check: PASSED
- All 2 created files exist on disk
- All 6 commit hashes verified in git log
- `python -c "from services.review_service import ReviewService; from controllers.review_controller import ReviewController"` — no ImportError

---
*Phase: 11-hitl-data-model-backend*
*Plan: 02*
*Completed: 2026-07-18*
