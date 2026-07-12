---
phase: 03-cleanup-testing
plan: 01
subsystem: evaluation
tags: [archive, cleanup, di-container, controller, pipeline]
requires:
  - "02-04: PipelineService must exist (prerequisite for wiring)"
provides:
  - "Clean separation: old engine in archive/, PipelineService as sole engine"
  - "Updated ServiceContainer with PipelineService"
  - "Updated controller with new evaluate_session_repositories() return shape"
affects:
  - services/container.py
  - services/__init__.py
  - controllers/evaluation_controller.py
  - .gitignore
tech-stack:
  added: []
  patterns: [archive-as-reference-artifact, threat-model-mitigation-in-di]
key-files:
  created:
    - archive/main.py
    - archive/evaluation_service.py
  modified:
    - services/container.py
    - services/__init__.py
    - controllers/evaluation_controller.py
    - .gitignore
decisions: []
metrics:
  duration_minutes: 15
  completed_date: "2026-07-12"
tasks_total: 2
tasks_completed: 2
---

# Phase 3 Plan 1: Archive & Wire PipelineService Summary

Archived the old monolithic evaluation engine (main.py) and subprocess wrapper (evaluation_service.py) under `archive/` with git history preserved. Wired `PipelineService` as the sole evaluation engine in the DI container and updated all three controller endpoints to use `evaluate_session_repositories()` with the new `{evaluated, results}` return shape.

## Completed Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Archive old evaluation engine and subprocess wrapper | `8aee466` | archive/main.py, archive/evaluation_service.py, .gitignore |
| 2 | Wire PipelineService in ServiceContainer and update controller | `fe9bae4` | services/container.py, services/__init__.py, controllers/evaluation_controller.py |

**Note:** Task 1 was already completed in a prior commit (`8aee466`) before this plan's execution. Verification confirmed all artifacts (shebang, archive comment, .gitignore entry) are present.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security/Missing Critical] Added try/except around PipelineService instantiation (T-03-02)**
- **Found during:** Task 2 (container.py build method)
- **Issue:** Threat model T-03-02 identifies PipelineService default constructor creating a full dependency chain as a DoS risk if construction fails. The plan's Step 1 snippet omitted the try/except.
- **Fix:** Wrapped `PipelineService()` in try/except with `raise RuntimeError(...) from exc`
- **Files modified:** services/container.py
- **Commit:** `fe9bae4`

## Verification Results

| Check | Status |
| ---- | ------ |
| `archive/main.py` exists with shebang | ✅ Pass |
| `archive/evaluation_service.py` exists with archive comment | ✅ Pass |
| `services/container.py` imports PipelineService (not EvaluationService) | ✅ Pass |
| `services/__init__.py` does NOT export EvaluationService | ✅ Pass |
| Controller calls `evaluate_session_repositories()` (not `evaluate_pending()`) | ✅ Pass |
| Controller response includes `evaluated` (int) and `results` (list) | ✅ Pass |
| All modules import without errors | ✅ Pass |
| `archive/` is in `.gitignore` | ✅ Pass |
| PipelineService is the only evaluation engine in active codebase | ✅ Pass |

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

All artifacts verified: archive files exist with correct annotations, container imports PipelineService successfully, services/__init__.py no longer exposes EvaluationService, controller returns updated shape.
