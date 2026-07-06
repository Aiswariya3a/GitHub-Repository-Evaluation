# AGENTS.md — GSD Workflow Guidance

This project uses the **Get Shit Done (GSD)** workflow system.

## Commands

- `/gsd-new-project` — Initialize project
- `/gsd-map-codebase` — Map existing codebase
- `/gsd-plan-phase <n>` — Plan a specific phase
- `/gsd-execute-phase <n>` — Execute a phase
- `/gsd-discuss-phase <n>` — Discuss a phase
- `/gsd-ui-phase <n>` — Generate UI design contract
- `/gsd-code-review` — Review code quality
- `/gsd-progress` — Check project status
- `/gsd-transition` — Transition between phases

## Project State

See `.planning/STATE.md` for current phase and progress.

## Core Value

Accurately evaluate student code against any instructor-defined rubric using a modular, rubric-agnostic pipeline of specialized SLM agents — where every evaluation is reproducible, evidence-based, and debugging is straightforward.

## Key Files

- `.planning/PROJECT.md` — Project context
- `.planning/REQUIREMENTS.md` — Scoped requirements with REQ-IDs
- `.planning/ROADMAP.md` — Phase structure
- `.planning/config.json` — Workflow preferences
- `.planning/codebase/` — Codebase analysis
- `.planning/research/` — Domain research

## Evaluation Pipeline Architecture

The new pipeline replaces the monolithic Gemini evaluation with a multi-agent SLM system:
- **Ingestion** (Phase 1): Clone, parse, extract capabilities independently
- **Agents** (Phase 2): Specialized SLM agents via Ollama with JSON contracts
- **Cleanup** (Phase 3): Remove old engine, add tests

## Workflow Mode

Interactive — each step requires confirmation.
