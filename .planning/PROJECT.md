# Automated GitHub Repository Evaluation — Multi-Agent SLM Pipeline

## What This Is

A web-based evaluation system that assesses student GitHub repositories against instructor-defined rubrics using a modular pipeline of specialized small language model (SLM) agents running on Ollama. The system ingests repositories, extracts capabilities via focused agents, evaluates each rubric criterion independently, and produces scored reports with feedback.

## Core Value

Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

## Current State

**Shipped:** v3.0 — Executive AI Dashboard & Async Evaluation (2026-07-18)
**Total shipped:** v1.0 SLM Pipeline (2026-07-12) + v2.0 Frontend Dashboard (2026-07-13) + v3.0 Executive Dashboard (2026-07-18)
**Phases:** 10 phases (5 planned + 5 direct-ship), 16 plans + 15 commits
**Tests:** 110 passing (2 integration gated)
**Commits:** 15 for v3.0 (61 files changed, +5,411 lines)
**Architecture:** Multi-agent SLM pipeline with Ollama + Flask frontend dashboard (async evaluation)
**Tech stack:** Python 3.11+, PostgreSQL, Ollama, Flask, pytest, Vanilla JS

All 45 v1 requirements implemented and verified. v2.0 frontend dashboard fully enhanced. v3.0 added async non-blocking evaluation with real-time progress tracking, collaboration analytics (equity waterfall, contributor profiles, network graph), redesigned Code Quality tab as an AI Assessment Report, Executive AI Dashboard Overview tab with grade letter presentation, Settings page with system diagnostics, light mode theme, command palette (Ctrl+K), dynamic repo avatars, and a simplified dashboard for non-technical evaluators. The old monolithic Gemini-based evaluation engine has been fully replaced with a modular pipeline supporting parallel agent execution, deterministic score aggregation, and file-based recovery.

## Requirements

### Validated

**v1.0 — SLM Pipeline:**
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

**v2.0 — Frontend Dashboard:**
- ✓ PDF report generation pipeline fix (lazy import, circular dependency resolved) — v2.0
- ✓ Ingestion snapshot + evaluation detail tabs with confidence badges — v2.0
- ✓ Plagiarism detection display, low-confidence filter, analytics enhancement — v2.0
- ✓ JavaScript extraction to dedicated files with shared utilities — v2.0
- ✓ CSS organization, error handling, skeleton loading, styled flash messages — v2.0

**v3.0 — Executive AI Dashboard & Async Evaluation:**
- ✓ Collaboration analytics with equity waterfall, contributor profiles, network graph, health score — v3.0
- ✓ Code Quality tab redesigned as AI Assessment Report with verdict, dimensions, evidence — v3.0
- ✓ Executive AI Dashboard Overview tab with grade letter, strengths/improvements, recommendations — v3.0
- ✓ Async evaluation with background threads and real-time progress tracking — v3.0
- ✓ Settings page with system diagnostics and `/api/system/status` endpoint — v3.0
- ✓ Light mode theme with localStorage persistence — v3.0
- ✓ Dashboard simplified for non-technical evaluators (KPI metrics, health card, leaderboard) — v3.0
- ✓ Enhanced PDF report generation (rubric-aware, per-repository, dynamic) — v3.0
- ✓ Feedback Agent summary field with retry and fallback synthesis — v3.0
- ✓ Global UX enhancements (font size increase, Ctrl+K palette, repo avatars, skeleton states) — v3.0

### Active

No active requirements remain. Next milestone (v4.0) will define new requirements.

### Out of Scope

- OAuth/authentication — application assumes trusted network
- Mobile app — web-only
- Real-time streaming of evaluation results
- Multi-tenant/SaaS deployment
- Containerization/Docker — no immediate plan
- Support for binary/non-text file evaluation
- Live collaborative editing features

## Context

Shipped v3.0 Executive AI Dashboard & Async Evaluation on top of v1.0 + v2.0. Three milestones complete. Current codebase:

- **Language:** Python 3.11+, Vanilla JavaScript (ES6)
- **Database:** PostgreSQL with 3 migrations + schema additions for progress tracking, rich GitHub metadata
- **SLM runtime:** Ollama with Qwen2.5-Coder 3B (code) and Phi-4 Mini (reasoning)
- **Tests:** 110 passing (100 non-integration + 10 _set_nested + 2 integration gated)
- **Architecture:** Modular pipeline: ingestion → 3 parallel capability agents → rubric evaluation → aggregation → feedback → persistence (async, non-blocking with background threads)
- **Frontend:** Flask templates with 6 extracted JS files (common.js, session.js, dashboard.js, repository.js, reports.js, settings.js), organized CSS (light + dark mode via data-theme), command palette, dynamic repo avatars, no framework dependency
- **Key design decisions:** Background thread async evaluation, progress polling, collaboration analytics equity waterfall, grade letter (A-F) overview, AI Assessment Report terminology, CSS custom properties for theming, common.js `window.*` shared utilities

Prior codebase mapping at `.planning/codebase/` documents the full architecture, stack, conventions, and concerns.

## Next Milestone Goals

The v1.0 pipeline + v2.0 dashboard + v3.0 Executive Dashboard are all fully shipped. Next milestone:

- **v4.0 — Human-in-the-Loop Review** — dashboard review queue, instructor+admin review, low-confidence flagging, manual score overrides with reasoning notes, full audit trail, visual badges + report notes

Future milestones could also include:
- Local LLM upgrade (new SLM models: Qwen3-Coder, DeepSeek-Coder, etc.)
- Additional capability agents (Documentation Analysis, Complexity Analysis)
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
| Lazy import in report_service.generate() | Breaks circular dependency (pdf_gen -> services -> pdf_gen) | ✓ Good — standard Python pattern |
| session_context() returns 4-tuple | Plagiarism data needs without breaking existing callers | ✓ Good — backward compatible |
| Shared JS utilities on window.* | Cross-file access without a bundler | ✓ Good — simple, works with Flask static serving |
| 3 DOMContentLoaded handlers in dashboard.js | One file serves dashboard, overview, analytics pages | ✓ Good — avoids separate files for each page |
| CSS section headers (BASE/LAYOUT/COMPONENTS/STATES/RESPONSIVE) | Maintainability without a CSS preprocessor | ✓ Good — clear organization |
| Background threads for async evaluation | Simplest approach for Flask; no Celery/RQ dependency | ✓ Good — works for current scale |
| progress_pct + current_step on repositories | Avoids new progress table; sufficient granularity for polling | ✓ Good — minimal schema change |
| Dashboard: remove Action Center + Recent Sessions | Non-technical evaluators found them distracting | ✓ Good — cleaner landing page |
| Light mode via CSS custom properties + data-theme | Clean separation, no CSS preprocessor, instant toggle | ✓ Good — works across all pages |
| Grade letter (A-F) on Overview | Faculty evaluators need at-a-glance scoring | ✓ Good — immediately useful |
| Code Quality → "AI Assessment Report" | Faculty evaluators prefer "assessment" over "quality" | ✓ Good — better terminology fit |

## Evolution

This document evolves at phase transitions and milestone boundaries.

- **v1.0 shipped:** All 45 requirements moved to Validated. Full review completed. Core Value confirmed correct. Out of Scope audit passed.
- **v2.0 shipped:** Frontend Dashboard archived. 5 UI items added to Validated. 6 new Key Decisions recorded.
- **v3.0 shipped:** Executive AI Dashboard & Async Evaluation archived. 53 requirements documented retroactively. 5 logical phases (6-10) shipped directly as 15 commits. 6 new Key Decisions recorded.

---
*Last updated: 2026-07-18 after v3.0 milestone audit*
