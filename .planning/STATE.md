# STATE.md

> Project memory for the multi-agent SLM evaluation pipeline.

---

## Project Reference

**Core Value:** Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

**Current Focus:** Build the independent ingestion pipeline — the data foundation that all agents depend on.

---

## Current Position

- **Milestone:** 1.0 — SLM Pipeline Replacement
- **Phase:** 1 (Ingestion Pipeline)
- **Phase Status:** Plans created
- **Current Plan:** 01-01-PLAN.md (Wave 1 — Foundation Layer)
- **Plan Status:** Not started
- **Overall Progress:** [###-------------------] 0%

---

## Performance Metrics

| Metric | Value | Target | Notes |
|--------|-------|--------|-------|
| Total v1 requirements | 45 | 45 | ✓ Fully scoped |
| Mapped to phases | 45 | 45 | ✓ 100% coverage |
| Phases defined | 3 | 3-5 | ✓ Coarse granularity |
| Plans created | 0 | — | Context ready — awaiting gsd-plan-phase |
| Plans completed | 0 | — | — |

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

### Last Session
- Initialized project structure
- Created PROJECT.md, REQUIREMENTS.md, config.json
- Ran research phase
- Created ROADMAP.md and STATE.md
- Discussed Phase 1 (Ingestion Pipeline) — context captured

### Next Session
- Run `/gsd-plan-phase 1` to create plans for Phase 1 (Ingestion Pipeline)

---

*Last updated: 2026-07-06 (Phase 1 context gathered)*
