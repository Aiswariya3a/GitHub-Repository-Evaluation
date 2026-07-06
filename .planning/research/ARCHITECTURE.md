# Architecture Research

**Date:** 2026-07-06

## Recommended Architecture: Multi-Agent SLM Pipeline

### High-Level Flow

```
HTTP Trigger (/api/sessions/<id>/evaluate)
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Python)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Stage 1:     │  │ Stage 2:     │  │ Stage 3:                │ │
│  │ Ingestion    │─▶│ Capability   │─▶│ Rubric Evaluation       │ │
│  │ (sequential) │  │ Extraction   │  │ (per-criterion,         │ │
│  │              │  │ (parallel)   │  │  parallelizable)        │ │
│  └──────────────┘  └──────────────┘  └───────────┬─────────────┘ │
│                                                   │               │
│  ┌────────────────────────────────────────────────▼──────────────┐│
│  │ Stage 4: Score Aggregation (deterministic Python)             ││
│  │ Stage 5: Feedback Generation (SLM call)                       ││
│  │ Stage 6: Persist to PostgreSQL                                ││
│  └───────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### Stage Breakdown

**Stage 1 — Ingestion (Sequential)**
1. Clone repository (Git subprocess)
2. Fetch GitHub metadata (commits, contributors, PRs, issues)
3. Discover files (language-agnostic, by extension + shebang)
4. Parse source files (extract functions, classes, imports, docstrings)
5. Compute code metrics (lines, cyclomatic complexity, comment ratio)
6. Compare with base repository if configured
7. Write structured JSON to `{session_dir}/ingestion/`
8. Persist metadata to PostgreSQL

**Stage 2 — Capability Extraction (Parallel, Independent Agents)**
- Repository Understanding Agent
- Code Understanding Agent
- Collaboration Analysis Agent
Each reads from `{session_dir}/ingestion/`, writes to `{session_dir}/capabilities/`.

**Stage 3 — Rubric Evaluation (Per-Criterion, Parallel)**
1. Orchestrator loads rubric from PostgreSQL
2. For each criterion, creates a dedicated working directory
3. Rubric Evaluation Agent runs per-criterion, receiving only relevant evidence
4. Writes `{session_dir}/evaluation/{criterion_key}.json`
5. All criteria evaluated in parallel (they're independent)

**Stage 4 — Score Aggregation (Deterministic Python)**
- Sum criterion scores
- Clamp to rubric maximums
- Calculate percentages
- No LLM involved

**Stage 5 — Feedback Generation (Single SLM Call)**
- Receives all criterion scores + evidence
- Generates strengths, weaknesses, actionable feedback
- Writes to `{session_dir}/feedback.json`

**Stage 6 — Persist to PostgreSQL**
- Save evaluation results, scores, evidence, feedback

### Parallelism Opportunities

| Stage | Parallelism | Description |
|-------|-------------|-------------|
| Ingestion | Sequential | Cloning → Metadata → Parse → Metrics (data dependency chain) |
| Capability Extraction | **Fully parallel** | Repo Understanding, Code Understanding, Collaboration Analysis are independent |
| Rubric Evaluation | **Fully parallel** | Each criterion is independent; uses only extracted evidence |
| Score Aggregation | Sequential | Deterministic; requires all criterion scores |
| Feedback Generation | Sequential | Requires all scores + evidence |

### Agent Communication Pattern

```
Orchestrator
  │
  ├── Spawn Agent (subprocess)
  │     python agent_repo_understanding.py --input input.json --output output.json
  │
  ├── Wait for completion
  │
  ├── Validate output JSON against schema
  │
  ├── Read validated output
  │
  └── Pass relevant data to next agent (as file paths)
```

Each agent:
1. Reads its input JSON from a file path
2. Calls Ollama with its specific system prompt
3. Validates the SLM response against a JSON schema
4. Falls back: re-prompt on schema failure, mark partial on repeated failure
5. Writes structured output JSON to the specified output path
6. Exits with code 0 (success) or 1 (partial/failure)

### Configuration-Driven Design

New agents can be added by:
1. Creating a Python module with the agent class
2. Defining input/output JSON schemas
3. Registering in the orchestrator's agent registry
4. Adding to the pipeline configuration

No changes to the orchestrator core needed.

---
*Architecture research: 2026-07-06*
