# Automated GitHub Repository Evaluation — Multi-Agent SLM Pipeline

## What This Is

A web-based evaluation system that assesses student GitHub repositories against instructor-defined rubrics. The evaluation engine is being redesigned from a single monolithic LLM prompt into a pipeline of specialized small language model (SLM) agents running on Ollama. The system ingests repositories, extracts capabilities via focused agents, evaluates each rubric criterion independently, and produces scored reports with feedback.

## Core Value

Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

## Requirements

### Validated

Existing capabilities preserved from the current codebase:

- ✓ Repository validation (public + README check) — existing
- ✓ Automated cloning via git subprocess — existing
- ✓ GitHub API integration (commit count, metadata) — existing
- ✓ Plagiarism detection (TF-IDF + cosine similarity) — existing
- ✓ PDF report generation (individual + consolidated via ReportLab) — existing
- ✓ Session management (CRUD, resume, archive) — existing
- ✓ Custom rubric creation, versioning, and per-session assignment — existing
- ✓ PostgreSQL persistence with normalized schema — existing
- ✓ Flask web dashboard with server-rendered templates — existing
- ✓ Search across sessions and repositories — existing

### Active

- [ ] **ING-01**: Independent data ingestion pipeline — clones repo, fetches GitHub metadata (commits, contributors, PRs, issues), parses source files, extracts functions/structures/metrics, stores both to JSON files and PostgreSQL
- [ ] **ING-02**: Language-agnostic file discovery — dynamically detects file types instead of relying on fixed paths or extensions
- [ ] **ING-03**: Base repository comparison — computes delta between student and base repo during ingestion
- [ ] **ORC-01**: Python orchestrator — manages workflow, schedules agents (parallel where possible), handles retries, aggregates scores, stores results
- [ ] **ORC-02**: Configurable execution mode — subprocess (default) or in-process agent execution
- [ ] **AGN-01**: Repository Understanding Agent — identifies languages, discovers important files, summarizes project structure, outputs structured JSON
- [ ] **AGN-02**: Code Understanding Agent — analyzes implementation, extracts capabilities, detects algorithms, APIs, data structures, functions, file operations, error handling
- [ ] **AGN-03**: Collaboration Analysis Agent — analyzes commits, contributors, PRs, issues, collaboration metrics
- [ ] **AGN-04**: Rubric Evaluation Agent — evaluates one criterion at a time using extracted evidence; returns score, confidence, evidence, remarks
- [ ] **AGN-05**: Feedback Generation Agent — generates strengths, weaknesses, and actionable feedback from criteria evaluations
- [ ] **OLL-01**: Ollama integration — configurable host/port, automatic model selection per agent type (Qwen2.5-Coder 3B for code tasks, Phi-4 Mini for reasoning/feedback)
- [ ] **OLL-02**: Model routing — route requests to the appropriate SLM based on agent role
- [ ] **TST-01**: Unit tests for each agent
- [ ] **TST-02**: Integration tests for the full pipeline
- [ ] **CLN-01**: Remove monolithic evaluation engine from `main.py`
- [ ] **CLN-02**: Clear existing evaluation results from database

### Out of Scope

- OAuth/authentication — application assumes trusted network
- Mobile app — web-only
- Real-time streaming of evaluation results
- Multi-tenant/SaaS deployment
- Containerization/Docker — no immediate plan
- Support for binary/non-text file evaluation
- Live collaborative editing features

## Context

**Current state:** A functional Flask-based evaluation system where a single Gemini prompt handles repository understanding, code analysis, rubric scoring, and feedback generation. The monolithic approach produces large prompts, inconsistent scoring, and is difficult to debug or customize.

**Target state:** A modular pipeline running local SLMs via Ollama. Each agent has a single responsibility and receives only the context it needs. Agents communicate via structured JSON files on disk. The orchestrator handles workflow, parallelism, and deterministic score aggregation.

**Prior codebase mapping** exists at `.planning/codebase/` documenting the full architecture, stack, conventions, and concerns.

## Constraints

- **Runtime**: Python 3.11+, Ollama with Qwen2.5-Coder 3B and Phi-4 Mini models
- **Database**: PostgreSQL (existing schema preserved)
- **Hardware**: Configurable Ollama host/port — supports local CPU, local GPU, or remote server
- **Inference speed**: 1–3 minutes per repository is acceptable; accuracy is the priority
- **No production deployment** — Flask dev server is sufficient for current use
- **Existing rubric format** preserved — categories with criteria, each criterion has a `criterion_key`, `name`, and `max_score`; points-based scoring

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Complete replacement, not gradual migration | No production users; avoids dual-maintenance complexity | — Pending |
| Refactor `main.py` into orchestrator | Preserves CLI pattern and subprocess architecture; orchestrator becomes the new evaluator | — Pending |
| Hybrid orchestration | Central orchestrator for high-level flow; agents can run in parallel chains | — Pending |
| JSON files on disk for agent communication | Simple, debuggable, decouples agents from each other and from the database | — Pending |
| Keep Flask UI | Existing dashboard works; update templates to show multi-agent results | — Pending |
| Two SLM models | Qwen2.5-Coder 3B for code understanding tasks; Phi-4 Mini for reasoning/feedback | — Pending |
| Configurable Ollama host/port | Supports local dev, CI, and remote GPU server | — Pending |
| Configurable execution mode | Default subprocess; in-process available for debugging | — Pending |
| Language-agnostic ingestion | Build generic framework from start; dynamic file type detection | — Pending |
| Partial results on agent failure | Continue with available data; note which agents failed | — Pending |
| Preserve existing rubric format and scoring model | Categories + criteria with points; no changes needed | — Pending |
| Clear existing evaluation results | Fresh start; no backward compatibility needed | — Pending |
| Trigger via same HTTP endpoint | Replace `evaluation_service.py` subprocess call with orchestrator | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-06 after initialization*
