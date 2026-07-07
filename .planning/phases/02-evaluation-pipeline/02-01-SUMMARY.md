---
phase: 02-evaluation-pipeline
plan: 01
subsystem: evaluation
tags: [ollama, slm, json-schema, agent-base, model-routing]

# Dependency graph
requires:
  - phase: 01-ingestion-pipeline
    provides: [ProjectSnapshot data structures, service patterns]
provides:
  - OllamaClient with model routing (code vs reasoning) and temperature=0 enforcement
  - BaseAgent abstract class with run() contract and validation utilities
  - All 5 JSON Schema definitions for agent output validation
  - Evaluation subpackage structure for downstream agents
affects: [02-02-capability-agents, 02-03-rubric-evaluation, 02-04-orchestrator]

# Tech tracking
tech-stack:
  added: [requests (direct HTTP), jsonschema (existing)]
  patterns:
    - "Agent base class with run() interface (per D-01)"
    - "JSON Schema draft-07 for all agent output contracts"
    - "Ollama raw HTTP calls (not Python SDK) for SLM stability"

key-files:
  created:
    - services/ollama_client.py
    - services/evaluation/__init__.py
    - services/evaluation/agent_base.py
    - services/evaluation/schemas.py
  modified:
    - services/__init__.py
    - .env
    - .gitignore

key-decisions:
  - "D-01: Agents are in-process Python classes with run(snapshot: dict) -> dict interface"
  - "Ollama client uses raw HTTP (requests library) instead of official ollama Python SDK for better SLM output control"
  - "Qwen2.5-Coder 3B for code agents, Phi-4 Mini 3.8B for reasoning/feedback agents"
  - "All 5 JSON schemas are self-contained (no $ref) for direct use with jsonschema.validate()"
  - "Model names configurable via OLLAMA_CODE_MODEL and OLLAMA_REASONING_MODEL env vars"

patterns-established:
  - "Dependency injection: agents receive pre-configured OllamaClient instance"
  - "Execution mode passthrough: subprocess flag set on agent, spawning handled by orchestrator"
  - "Idempotent output writing: agents can write validated output to unique file paths (D-11)"
  - "Temperature=0 enforced silently: non-zero values logged as warning but overridden"
  - "Response validation: OllamaClient validates/normalizes all SLM responses before returning"

requirements-completed: [OLL-01, OLL-02, OLL-03, OLL-04, OLL-05, AGN-06]

# Metrics
duration: 10min
completed: 2026-07-07
---

# Phase 2 Plan 01: Foundation Layer Summary

**Ollama HTTP client with model routing (Qwen2.5-Coder 3B / Phi-4 Mini), temperature=0 enforcement, BaseAgent abstract class with `run()` contract, and 5 self-contained JSON Schema draft-07 definitions for all agent output types**

## Performance

- **Duration:** 10 min (16:05-16:14 IST)
- **Started:** 2026-07-07T10:35:00Z
- **Completed:** 2026-07-07T10:44:24Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- `OllamaClient` class with configurable host/port (env vars), model routing (code → Qwen2.5-Coder 3B, reasoning → Phi-4 Mini), `validate_connectivity()` startup check, and `infer()` with temperature=0 enforcement
- `BaseAgent` abstract class with `run(input_data, output_path)` contract, `_write_output()` for idempotent file persistence, and `_validate_output()` for JSON Schema validation via `jsonschema`
- 5 complete JSON Schema draft-07 definitions: `REPO_UNDERSTANDING_SCHEMA`, `CODE_UNDERSTANDING_SCHEMA`, `COLLABORATION_SCHEMA`, `CRITERION_EVALUATION_SCHEMA`, `FEEDBACK_SCHEMA`
- `services/evaluation/` subpackage created with proper `__init__.py` exports
- `services/__init__.py` updated to export `OllamaClient`
- `.env` updated with Ollama configuration variables and sensible defaults
- `.gitignore` updated with `__pycache__/` and `*.pyc` patterns

## Task Commits

Each task was committed atomically:

1. **task 1: Create Ollama client with model routing and startup validation** - `4a80073` (feat)
2. **task 2: Create BaseAgent abstract class with in-process/subprocess interface** - `bace494` (feat)
3. **task 3: Define JSON Schema contracts for all agent outputs** - `b66f25f` (feat)

**Cleanup commit:** `707e05b` (chore: remove tracked pycache files)

## Files Created/Modified

### Created
- `services/ollama_client.py` - Ollama HTTP client with `OllamaClient`, `OllamaConnectionError`, `OllamaModelNotFoundError`, `OllamaAPIError`
- `services/evaluation/__init__.py` - Package init exporting `BaseAgent` and all 5 schema constants
- `services/evaluation/agent_base.py` - Abstract `BaseAgent` with `run()`, `_write_output()`, `_validate_output()`
- `services/evaluation/schemas.py` - JSON Schema definitions for all agent output types

### Modified
- `services/__init__.py` - Added `OllamaClient` to exports
- `.env` - Added `OLLAMA_HOST`, `OLLAMA_PORT`, `OLLAMA_TIMEOUT`, `OLLAMA_CODE_MODEL`, `OLLAMA_REASONING_MODEL`
- `.gitignore` - Added `__pycache__/` and `*.pyc` patterns

## Decisions Made

All decisions followed the Phase 2 context document (02-CONTEXT.md):
- **D-01:** Agents are in-process Python classes with `run()` interface (implemented via `BaseAgent`)
- **D-02:** Execution mode passthrough via config flag (default `"in_process"`)
- **D-11:** Idempotent file-based recovery via `_write_output()`
- Raw HTTP to Ollama API (not Python SDK) for SLM output stability — avoids dependency issues
- Model names configurable via environment variables with sensible defaults
- All schemas are self-contained (no `$ref`) for direct use with `jsonschema.validate()`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `services/evaluation/__init__.py` depended on `schemas.py` (Task 3) for imports. Resolved by creating schemas.py alongside Task 2 files, then committing as separate tasks.
- `__pycache__` directories were previously tracked by git. Added `.gitignore` patterns and `git rm --cached` to clean them up. These were tracked from Phase 1 commits.

## Threat Surface Scan

No new threat surface beyond what's documented in the plan's `<threat_model>`:
- **T-02-01 (Tampering/OllamaClient.infer response):** MITIGATED — response is parsed and validated; `OllamaAPIError` raised on bad format
- **T-02-02 (Spoofing/env vars):** ACCEPTED — local-only deployment
- **T-02-03 (Tampering/JSON Schema):** ACCEPTED — version-controlled code

## User Setup Required

**External services require manual configuration:**
1. Install Ollama from [ollama.com](https://ollama.com)
2. Pull required models:
   ```bash
   ollama pull qwen2.5-coder:3b
   ollama pull phi-4-mini:3.8b
   ```
3. Configure `.env` (optional — defaults work for localhost:11434):
   ```
   OLLAMA_HOST=http://localhost
   OLLAMA_PORT=11434
   OLLAMA_CODE_MODEL=qwen2.5-coder:3b
   OLLAMA_REASONING_MODEL=phi-4-mini:3.8b
   ```
4. Test connectivity: `python -m services.ollama_client`

## Known Stubs

None identified — all files contain fully functional code.

## Self-Check: PASSED

- [x] `services/ollama_client.py` exists (315 lines) — verified import OK
- [x] `services/evaluation/agent_base.py` exists (87 lines) — verified import OK, abstract check passes
- [x] `services/evaluation/schemas.py` exists (279 lines) — all 5 schemas validate as valid draft-07
- [x] `services/evaluation/__init__.py` exists — exports BaseAgent and all schema constants
- [x] `services/__init__.py` updated — exports OllamaClient
- [x] `.env` updated with Ollama configuration
- [x] All 4 commits exist in git log

## Next Phase Readiness

- Foundation layer ready for Wave 2 parallel execution:
  - `02-02-PLAN.md` — Capability Extraction Agents (depends on BaseAgent, OllamaClient, schemas)
  - `02-03-PLAN.md` — Rubric Evaluation (depends on BaseAgent, OllamaClient, schemas)
- Both downstream plans can import from `services.evaluation` and `services.ollama_client`
- Agent output schemas are importable and validated — downstream agents know their contract
- No blockers for Wave 2

---

*Phase: 02-evaluation-pipeline*
*Completed: 2026-07-07*
