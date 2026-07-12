# Roadmap: Multi-Agent SLM Evaluation Pipeline

**Core Value:** Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

**Granularity:** Coarse (3 phases)
**Parallel execution:** Enabled
**Generated:** 2026-07-06

---

## Phases

- [x] **Phase 1: Ingestion Pipeline** — Build independent data ingestion: clone repos, discover files, parse code, compute metrics, persist to JSON and PostgreSQL (completed 2026-07-07)
- [x] **Phase 2: Evaluation Pipeline** — Build agents, orchestrator, Ollama integration, rubric evaluation, and feedback generation; full end-to-end pipeline (completed 2026-07-12)
- [ ] **Phase 3: Cleanup & Testing** — Remove old monolithic engine, clear old data, add unit/integration/contract tests

---

## Phase Dependencies

```
Phase 1 (Ingestion)
    │
    ▼
Phase 2 (Evaluation) ─── depends on ingestion data
    │
    ▼
Phase 3 (Cleanup & Testing) ─── depends on new pipeline existing
```

---

## Phase Details

### Phase 1: Ingestion Pipeline

**Goal:** System can independently clone, analyze, and persist student repository data — source files, code metrics, and GitHub metadata — as structured JSON and in PostgreSQL.

**Depends on:** Nothing (foundation phase)

**Requirements:** ING-01, ING-02, ING-03, ING-04, ING-05, ING-06, ING-07, ING-08

**Success Criteria** (what must be TRUE):
1. User submits a GitHub repository URL → system clones it into a working directory, discovers source files by extension and shebang, parses functions/classes/imports/docstrings, computes LOC/cyclomatic complexity/comment ratio, and stores structured results as JSON
2. User configures a base repository → system detects and records delta between student and base code during ingestion
3. System fetches GitHub metadata (commits, contributors, PRs, issues) via API and includes it in ingestion output
4. All ingestion artifacts exist as readable JSON files in the session working directory AND are persisted to PostgreSQL tables (repository metadata + code metrics)
5. Language-agnostic file discovery correctly identifies and parses Python, JavaScript, Java, and other common languages without hardcoded path patterns

**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — Foundation Layer: models, config, GitHub metadata, DB migration + repository
- [x] 01-02-PLAN.md — File Processing Pipeline: file discovery, code parsing, metrics, delta detection
- [x] 01-03-PLAN.md — Output & Orchestration: snapshot builder, JSON output, DB persistence, orchestrator

---

### Phase 2: Evaluation Pipeline

**Goal:** System evaluates repositories via specialized SLM agents orchestrated end-to-end — capability extraction, rubric scoring, and feedback generation — using local Ollama models with correct model routing, parallel execution, and graceful error handling.

**Depends on:** Phase 1 (agents read ingestion JSON; orchestrator depends on persisting results)

**Requirements:** AGN-01, AGN-02, AGN-03, AGN-04, AGN-05, AGN-06, EVA-01, EVA-02, EVA-03, EVA-04, EVA-05, EVA-06, EVA-07, FDB-01, FDB-02, FDB-03, ORC-01, ORC-02, ORC-03, ORC-04, ORC-05, ORC-06, ORC-07, OLL-01, OLL-02, OLL-03, OLL-04, OLL-05

**Success Criteria** (what must be TRUE):
1. User triggers an evaluation → orchestrator runs Repository Understanding, Code Understanding, and Collaboration Analysis agents in parallel; each reads from ingestion JSON and writes structured capability JSON validated against schema
2. For each rubric criterion loaded from PostgreSQL, the Rubric Evaluation Agent evaluates it independently with a score (clamped to rubric max), confidence level, supporting evidence, and evaluator remarks; all criteria run in parallel
3. The Feedback Agent receives all criterion scores and evidence, then generates distinct strengths, weaknesses, and actionable improvement suggestions; output is written to working directory JSON and PostgreSQL
4. If any agent fails (Ollama unavailable, bad output, timeout) → pipeline continues with partial results, logs which agents failed, and flags affected evaluations as low-confidence
5. All inference uses the correct Ollama model routing — code agents receive Qwen2.5-Coder 3B, feedback/reasoning agents receive Phi-4 Mini — with temperature=0 for reproducibility; Ollama connectivity is validated at startup
6. Final evaluation results (scores, evidence, feedback) are persisted to PostgreSQL and viewable in the existing dashboard

**Plans:** 4/4 plans complete

Plans:
- [x] 02-01-PLAN.md — Foundation: Ollama client, agent base class, JSON schemas (Wave 1)
- [x] 02-02-PLAN.md — Capability Extraction Agents: Repo Understanding, Code Understanding, Collaboration (Wave 2)
- [x] 02-03-PLAN.md — Rubric Evaluation: evidence routing, criterion evaluation, deterministic score aggregation (Wave 2)
- [x] 02-04-PLAN.md — Orchestrator, Feedback Agent, PostgreSQL persistence, PipelineService (Wave 3)

---

### Phase 3: Cleanup & Testing

**Goal:** Old monolithic evaluation engine is removed from the codebase, old evaluation data is cleared from the database, and the new pipeline is thoroughly tested with unit, integration, and contract tests.

**Depends on:** Phase 2 (new pipeline must exist before removing old engine; tests cover the new pipeline)

**Requirements:** TST-01, TST-02, TST-03, TST-04, CLN-01, CLN-02, CLN-03, CLN-04, CLN-05

**Success Criteria** (what must be TRUE):
1. The old single-prompt evaluation logic is removed from `main.py`; duplicate code paths (`evaluate_code` + `evaluate_code_dynamic`) are removed; dead code in `models/domain.py` is removed or archived — only the orchestrator-based pipeline exists as the sole evaluation engine
2. Old evaluation data is cleared from PostgreSQL tables — the database is clean for the new pipeline's results
3. Every agent has unit tests (with mocked Ollama responses) that pass; orchestrator unit tests cover workflow, retries, partial results, and error handling
4. A full pipeline integration test runs the complete pipeline (ingestion → agents → evaluation → feedback) against a real GitHub repository end-to-end and produces valid results
5. JSON Schema contract tests pass for all agent inputs and outputs — every schema validates correctly

**Plans:** 4 plans across 3 waves

Plans:
- [x] 03-01-PLAN.md — Archive Legacy Code + Wire PipelineService (Wave 1)
- [ ] 03-02-PLAN.md — Remove Old Domain Models + DB Migration (Wave 1)
- [ ] 03-03-PLAN.md — Test Infrastructure + Unit Tests (Wave 2)
- [ ] 03-04-PLAN.md — Orchestrator + Pipeline + Integration Tests (Wave 3)

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Ingestion Pipeline | 3/3 | Complete    | 2026-07-07 |
| 2. Evaluation Pipeline | 4/4 | Complete   | 2026-07-12 |
| 3. Cleanup & Testing | 1/4 | In progress | 2026-07-12 (Wave 1) |

---

## Coverage Map

| Category | Requirements | Phase |
|----------|-------------|-------|
| Ingestion Pipeline | ING-01 through ING-08 | Phase 1 |
| Capability Extraction Agents | AGN-01 through AGN-06 | Phase 2 |
| Rubric Evaluation | EVA-01 through EVA-07 | Phase 2 |
| Feedback Generation | FDB-01 through FDB-03 | Phase 2 |
| Orchestrator | ORC-01 through ORC-07 | Phase 2 |
| Ollama Integration | OLL-01 through OLL-05 | Phase 2 |
| Testing | TST-01 through TST-04 | Phase 3 |
| Cleanup | CLN-01 through CLN-05 | Phase 3 |

**Coverage:** 45/45 v1 requirements mapped ✓
