# Automated GitHub Repository Evaluation — Multi-Agent SLM Pipeline

## What This Is

A web-based evaluation system that assesses student GitHub repositories against instructor-defined rubrics using a modular pipeline of specialized small language model (SLM) agents running on Ollama. The system ingests repositories, extracts capabilities via focused agents, evaluates each rubric criterion independently, and produces scored reports with feedback.

## Core Value

Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

## Current State

**Shipped:** v1.0 — SLM Pipeline Replacement (2026-07-12)
**Phases:** 4 phases, 12 plans
**Tests:** 110 passing (2 integration gated)
**Architecture:** Multi-agent SLM pipeline with Ollama (Qwen2.5-Coder 3B + Phi-4 Mini)
**Tech stack:** Python 3.11+, PostgreSQL, Ollama, Flask, pytest

All 45 v1 requirements implemented and verified. The old monolithic Gemini-based evaluation engine has been fully replaced with a modular pipeline supporting parallel agent execution, deterministic score aggregation, and file-based recovery.

## Requirements

### Validated

- ✓ Independent data ingestion pipeline (ING-01 through ING-08) — v1.0
- ✓ Repository Understanding Agent (AGN-01) — v1.0
- ✓ Code Understanding Agent (AGN-02) — v1.0
- ✓ Collaboration Analysis Agent (AGN-03) — v1.0
- ✓ Parallel agent execution (AGN-04) — v1.0
- ✓ Schema-validated agent output (AGN-05, AGN-06) — v1.0
- ✓ Rubric evaluation with evidence routing (EVA-01 through EVA-07) — v1.0
- ✓ Feedback generation (FDB-01 through FDB-03) — v1.0
- ✓ Full pipeline orchestrator (ORC-01 through ORC-07) — v1.0
- ✓ Ollama integration with model routing (OLL-01 through OLL-05) — v1.0
- ✓ Unit/integration/schema tests (TST-01 through TST-04) — v1.0
- ✓ Legacy code cleanup (CLN-01 through CLN-05) — v1.0

### Active

No active v1 requirements remain. Next milestone will define v2 requirements.

### Out of Scope

- OAuth/authentication — application assumes trusted network
- Mobile app — web-only
- Real-time streaming of evaluation results
- Multi-tenant/SaaS deployment
- Containerization/Docker — no immediate plan
- Support for binary/non-text file evaluation
- Live collaborative editing features

## Context

Shipped v1.0 with the complete multi-agent SLM evaluation pipeline. The replacement of the monolithic Gemini-based engine is fully complete. Current codebase:

- **Language:** Python 3.11+
- **Database:** PostgreSQL with 3 migrations (ingestion_records, evaluation_results, archived old tables)
- **SLM runtime:** Ollama with Qwen2.5-Coder 3B (code) and Phi-4 Mini (reasoning)
- **Tests:** 110 passing (100 non-integration + 10 new _set_nested + 2 integration gated)
- **Architecture:** Modular pipeline: ingestion → 3 parallel capability agents → rubric evaluation → aggregation → feedback → persistence
- **Key design decisions:** File-based agent communication, deterministic score aggregation, configurable model routing, temperature=0 enforcement

Prior codebase mapping at `.planning/codebase/` documents the full architecture, stack, conventions, and concerns.

## Next Milestone Goals

The v1.0 requirements are fully shipped. Future milestones could include:

- Additional SLM models (Qwen3-Coder, DeepSeek-Coder)
- Additional capability agents (Documentation Analysis, Complexity Analysis)
- Human-in-the-loop review for low-confidence evaluations
- Performance benchmarks and optimization
- Containerization for deployment
- Multi-language parsing via tree-sitter

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
| Complete replacement, not gradual migration | No production users; avoids dual-maintenance complexity | ✓ Good — clean slate for new pipeline |
| Refactor `main.py` into orchestrator | Preserves CLI pattern; orchestrator becomes the new evaluator | ✓ Good — 6-step pipeline with file-based recovery |
| JSON files on disk for agent communication | Simple, debuggable, decouples agents from each other and from the database | ✓ Good — idempotent, easy to debug |
| Keep Flask UI | Existing dashboard works; update templates to show multi-agent results | ✓ Good — controller updated for new return shape |
| Two SLM models | Qwen2.5-Coder 3B for code; Phi-4 Mini for reasoning/feedback | ✓ Good — correct model routing for task types |
| Configurable Ollama host/port | Supports local dev, CI, and remote GPU server | ✓ Good — env vars with sensible defaults |
| Language-agnostic ingestion | Dynamic file type detection (extension + shebang) | ✓ Good — 12 languages supported |
| Partial results on agent failure | Continue with available data; note which agents failed | ✓ Good — resilient pipeline |
| Preserve existing rubric format | Categories + criteria with points; no changes needed | ✓ Good — backward compatible |
| Temperature=0 enforced silently | Reproducibility for all SLM inference | ✓ Good — overrides non-zero values with log warning |

## Evolution

This document evolves at phase transitions and milestone boundaries.

- **v1.0 shipped:** All 45 requirements moved to Validated. Full review completed. Core Value confirmed correct. Out of Scope audit passed.

---
*Last updated: 2026-07-12 after v1.0 milestone*
