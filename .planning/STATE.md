---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Frontend Dashboard
current_plan: 1/4
status: in_progress
last_updated: "2026-07-13T11:26:00.000Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 12
  completed_plans: 12
  percent: 100
---

# STATE.md

> Project memory for the multi-agent SLM evaluation pipeline.

---

## Project Reference

**Core Value:** Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

**Current Focus:** Milestone v1.0 complete — planning next milestone

---

## Current Position

Phase: 5 (Frontend Dashboard)

- **Milestone:** 2.0 — Frontend Dashboard
- **Phase:** 5
- **Phase Status:** In Progress
- **Plan 01:** Fix PDF report generation pipeline ✓ COMPLETE
- **Plan 02:** Ingestion snapshot + evaluation detail tabs: PENDING
- **Plan 03:** Collaboration tab + low-confidence filter + plagiarism view: PENDING
- **Plan 04:** Analytics page + UX polish: PENDING
- **Current Plan:** 1/4
- **Plan Status:** Plan 01 complete — pdf_gen.py refactored, report_service.py uses direct import
- **Overall Progress:** 12/12 plans complete across all phases

---

## Performance Metrics

| Metric | Value | Target | Notes |
|--------|-------|--------|-------|
| Total v1 requirements | 45 | 45 | ✓ Fully scoped |
| Mapped to phases | 45 | 45 | ✓ 100% coverage |
| Phases defined | 3 | 3-5 | ✓ Coarse granularity |
| Plans created | 11 | — | Phase 1 (3) + Phase 2 (4) + Phase 3 (4) |
| Plans completed | 11 | — | Phase 1 (3) + Phase 2 (4) + Phase 3 (3) |
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

### Last Session

- **Executed Phase 5 Plan 1 (05-01)** — Fix PDF Report Generation Pipeline complete:
  - Refactored pdf_gen.py from standalone CLI script into callable module with generate_pdf(session_id, output_dir) entry function
  - All module-level code guarded behind if __name__ == "__main__"
  - Updated resolve_rubric_snapshot(), build_question_table(), get_plagiarism() to accept parameters instead of closure variables
  - generate_preamble() and merge_pdfs() accept output_dir parameter
  - report_service.py updated to import generate_pdf directly (lazy import to break circular dependency)
  - Removed subprocess.run() from report generation flow

### Next Session

- Execute Phase 5 Plan 2: Ingestion snapshot + evaluation detail tabs
- Execute Phase 5 Plan 3: Collaboration tab + low-confidence filter + plagiarism view
- Execute Phase 5 Plan 4: Analytics page + UX polish

---

*Last updated: 2026-07-12 (Phase 3 Plan 1 complete)*
