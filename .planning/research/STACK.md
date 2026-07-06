# Technology Stack Research

**Date:** 2026-07-06

## Recommended Stack

### Core Runtime
- **Python 3.11+** — Existing project runtime, retained
- **Ollama** — Local SLM inference server (assumed pre-installed by user)

### SLM Models (Ollama)
- **Qwen2.5-Coder 3B** (`qwen2.5-coder:3b`) — Code understanding, repository analysis, capability extraction. Strong on structured JSON output for code tasks.
- **Phi-4 Mini** (`phi-4-mini:3.8b`) — Reasoning and scoring, rubric evaluation, feedback generation. Better at rubric interpretation and scoring than pure code models.

### Agent Communication
- **JSON files on disk** — Each agent writes structured output to a shared working directory. Orchestrator passes file paths, not raw data.
- **JSON Schema validation** — Every agent output validates against a predefined schema before the next agent consumes it.

### Orchestration
- **Pure Python** — No external orchestration framework. The orchestrator is a Python module that manages agent lifecycle, parallelism, and data flow. Simpler than introducing Airflow, Prefect, or LangChain for this scope.

### Persistence
- **PostgreSQL** — Existing, retained for final results, sessions, rubrics, reports.
- **JSON on disk** — Intermediate agent outputs stored in session-specific working directories.

### Key Python Packages
- `ollama` — Python client for Ollama API (sync + async)
- `jsonschema` — Validate agent output contracts
- `concurrent.futures` — Parallel agent execution (stdlib)
- `pathlib` — JSON file I/O (stdlib)
- Existing packages retained: `psycopg`, `flask`, `reportlab`, `scikit-learn`, `requests`

## Why Not

| Alternative | Reason |
|-------------|--------|
| LangChain/LlamaIndex | Overkill for focused agent pipeline; adds dependency complexity |
| FastAPI | Existing Flask app works; no benefit to swap |
| Message queue (Redis/RabbitMQ) | Unnecessary for single-machine pipeline; JSON files are simpler |
| Docker containers per agent | Too heavyweight for local SLM inference |
| GPU acceleration libraries | Ollama handles GPU detection automatically |

---
*Stack research: 2026-07-06*
