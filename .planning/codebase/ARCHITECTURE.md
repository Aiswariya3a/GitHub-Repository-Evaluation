<!-- refreshed: 2026-07-13 -->
# Architecture

**Analysis Date:** 2026-07-13

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                             │
│    Flask Blueprints: session_controller, repository_controller,       │
│    evaluation_controller, report_controller, rubric_controller        │
│    `controllers/*.py` + `templates/*.html` + `static/*.css`          │
├──────────────────────────────────────────────────────────────────────┤
│                        CONTROLLER LAYER                               │
│    `controllers/__init__.py`  (re-exports + barrel)                   │
│    `controllers/common.py`    (services() accessor, helpers)          │
│    Each controller = Blueprint + class wrapper                        │
├──────────────────────────────────────────────────────────────────────┤
│                        SERVICE LAYER                                  │
│    SessionService   `services/session_service.py`                     │
│    RepositoryService `services/repository_service.py`                 │
│    GitHubService     `services/github_service.py`                     │
│    RubricService     `services/rubric_service.py`                     │
│    IngestionService  `services/ingestion_service.py`                  │
│    PipelineService   `services/evaluation/pipeline_service.py`        │
│    ReportService     `services/report_service.py`                     │
│    AnalysisService   `services/analysis_service.py`                   │
├──────────────────────────────────────────────────────────────────────┤
│                    EVALUATION PIPELINE LAYER                           │
│    `services/evaluation/orchestrator.py`  EvaluationOrchestrator      │
│    `services/evaluation/agent_base.py`   BaseAgent (abstract)         │
│    `services/evaluation/repo_understanding_agent.py`                  │
│    `services/evaluation/code_understanding_agent.py`                  │
│    `services/evaluation/collaboration_agent.py`                       │
│    `services/evaluation/rubric_evaluation_agent.py`                   │
│    `services/evaluation/feedback_agent.py`                            │
│    `services/evaluation/score_aggregator.py`     (deterministic)      │
│    `services/evaluation/evidence_router.py`      (pre-filter)         │
│    `services/evaluation/schemas.py`              (JSON Schema)        │
│    `services/evaluation/ollama_router.py`        (system prompts)     │
│    `services/ollama_client.py`                  (HTTP client)         │
├──────────────────────────────────────────────────────────────────────┤
│                       INGESTION LAYER                                  │
│    `services/ingestion/file_discoverer.py`   FileDiscoverer            │
│    `services/ingestion/code_parser.py`       CodeParser                │
│    `services/ingestion/metrics_calculator.py` MetricsCalculator        │
│    `services/ingestion/delta_detector.py`    DeltaDetector             │
│    `services/ingestion/snapshot_builder.py`  SnapshotBuilder           │
├──────────────────────────────────────────────────────────────────────┤
│                     REPOSITORY / PERSISTENCE LAYER                     │
│    `repositories/session_repository.py`     SessionRepository          │
│    `repositories/repository_repository.py`  RepositoryRepository       │
│    `repositories/evaluation_repository.py`  EvaluationRepository       │
│    `repositories/ingestion_repository.py`   IngestionRepository        │
│    `repositories/rubric_repository.py`      RubricRepository           │
│    `database/postgres.py`               psycopg connection factory     │
│    `database/schema.sql`                Full DDL with indexes          │
│    `database/migration_*.sql`            Incremental migrations        │
├──────────────────────────────────────────────────────────────────────┤
│                        DOMAIN / MODEL LAYER                            │
│    `models/domain.py`            EvaluationSession, Repository         │
│    `models/evaluation_models.py`  CriterionEvaluation, CategoryScore,  │
│                                    AggregatedScore                     │
│    `models/ingestion_models.py`   ProjectSnapshot, delta types, etc.   │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `SessionController` | Session CRUD, dashboard, page routing | `controllers/session_controller.py` |
| `RepositoryController` | Repository CRUD, search, detail | `controllers/repository_controller.py` |
| `EvaluationController` | Evaluate/reevaluate endpoints | `controllers/evaluation_controller.py` |
| `ReportController` | PDF report generation endpoints | `controllers/report_controller.py` |
| `RubricController` | Rubric CRUD, versioning, duplicate | `controllers/rubric_controller.py` |
| `ServiceContainer` | Dependency injection composition root | `services/container.py` |
| `SessionService` | Session lifecycle (initialize DB, create, status) | `services/session_service.py` |
| `RepositoryService` | Repository lifecycle, hydration, dashboard | `services/repository_service.py` |
| `GitHubService` | GitHub API: clone, metadata, commits, PRs, issues | `services/github_service.py` |
| `IngestionService` | Clone → discover → parse → metrics → delta → snapshot | `services/ingestion_service.py` |
| `PipelineService` | High-level pipeline entry, wraps Orchestrator | `services/evaluation/pipeline_service.py` |
| `EvaluationOrchestrator` | 6-step pipeline: ingestion → agents → rubric → aggregate → feedback → persist | `services/evaluation/orchestrator.py` |
| `OllamaClient` | HTTP client for Ollama SLM inference | `services/ollama_client.py` |
| `BaseAgent` | Abstract agent contract: run(), validate, write | `services/evaluation/agent_base.py` |
| `RubricService` | Rubric version management, default seeding | `services/rubric_service.py` |
| `ReportService` | PDF generation via subprocess pdf_gen.py | `services/report_service.py` |
| `AnalysisService` | Legacy analysis wrapper | `services/analysis_service.py` |

## Pattern Overview

**Overall:** Layered architecture (Controllers → Services → Repositories → Database) with a multi-agent evaluation pipeline as the core domain logic.

**Key Characteristics:**
- Flask Blueprints for HTTP route modularization
- Explicit dependency injection via `ServiceContainer` composed in `app.py`
- Repository pattern for all PostgreSQL access (each table group gets a repository class)
- Multi-agent pipeline using `ThreadPoolExecutor` for parallel SLM inference
- File-based idempotency for pipeline step caching (`evaluations/{session}/{repo}/{step}.json`)
- JSON Schema validation for all LLM outputs (draft-07)
- Legacy tables (`evaluations`, `evaluation_questions`, `evaluation_criteria`) coexist alongside new pipeline tables (`evaluation_results`, `ingestion_records`)

## Layers

**Presentation (Controllers):**
- Purpose: HTTP request/response handling, route registration, template rendering
- Location: `controllers/`
- Contains: Flask Blueprints with route decorators; each controller wraps its blueprint in a class
- Depends on: `services` via `current_app.extensions["services"]` helper (`controllers/common.py`)
- Used by: Flask app factory in `app.py`

**Service Layer:**
- Purpose: Business logic orchestration, session/repo workflows, external integrations
- Location: `services/`
- Contains: `SessionService`, `RepositoryService`, `GitHubService`, `IngestionService`, `RubricService`, `ReportService`, `PipelineService`
- Depends on: `repositories/` for persistence, `database/` for connections
- Used by: Controllers

**Evaluation Pipeline (sub-layer within services):**
- Purpose: Multi-agent SLM evaluation of GitHub repositories against rubrics
- Location: `services/evaluation/`
- Contains: 5 agents (repo understanding, code understanding, collaboration, rubric evaluation, feedback), orchestrator, evidence router, score aggregator, schemas
- Depends on: `OllamaClient`, `IngestionService`, `RubricService`, repositories
- Used by: `PipelineService` → Controllers

**Ingestion Layer (sub-layer within services):**
- Purpose: Clone GitHub repos, discover files, parse code, compute metrics, build snapshots
- Location: `services/ingestion/`
- Contains: `FileDiscoverer`, `CodeParser`, `MetricsCalculator`, `DeltaDetector`, `SnapshotBuilder`
- Depends on: `GitHubService`, extension config at `config/extensions.json`
- Used by: `IngestionService`

**Repository Layer:**
- Purpose: PostgreSQL query encapsulation, CRUD operations, transactional writes
- Location: `repositories/`
- Contains: `SessionRepository`, `RepositoryRepository`, `EvaluationRepository`, `IngestionRepository`, `RubricRepository`
- Depends on: `database/postgres.py` (connection factory using `psycopg`)
- Used by: Services

**Database Layer:**
- Purpose: PostgreSQL connection management, schema initialization, migrations
- Location: `database/`
- Contains: `postgres.py` (connection factory, `initialize_database()`), `schema.sql`, migration files
- Depends on: `psycopg[binary]==3.2.9`
- Used by: Repositories

**Model/Domain Layer:**
- Purpose: Type contracts as frozen `@dataclass` objects for domain entities
- Location: `models/`
- Contains: `domain.py` (EvaluationSession, Repository), `evaluation_models.py` (pipeline types), `ingestion_models.py` (snapshot types)
- Used by: Services, tests

## Data Flow

### Primary Request Path — Repo Evaluation

1. **HTTP POST** → `evaluation_controller.py:evaluate_session()` or `evaluate_repository()` (`controllers/evaluation_controller.py:19,30`)
2. **Validation** — session active check via `SessionService.get_session()` (`controllers/evaluation_controller.py:7-11`)
3. **Delegation** → `PipelineService.evaluate_session_repositories()` (`services/evaluation/pipeline_service.py:49`)
4. **Orchestration** → `EvaluationOrchestrator.evaluate()` (`services/evaluation/orchestrator.py:196`)
5. **Step 1: Ingestion** — `IngestionService.ingest()` clones, parses, builds snapshot (`services/ingestion_service.py:37`)
6. **Step 2: Capability Extraction (parallel)** — RepoUnderstandingAgent, CodeUnderstandingAgent, CollaborationAgent run concurrently via `ThreadPoolExecutor` (`services/evaluation/orchestrator.py:266-286`)
7. **Step 3: Rubric Evaluation (parallel)** — One `RubricEvaluationAgent` call per rubric criterion, using pre-filtered evidence from `route_evidence()` (`services/evaluation/orchestrator.py:288-361`)
8. **Step 4: Score Aggregation** — Deterministic `aggregate_scores()` computes totals, normalizes to 20-point scale (`services/evaluation/score_aggregator.py:16`)
9. **Step 5: Feedback Generation** — `FeedbackAgent` generates strengths/weaknesses/suggestions (`services/evaluation/orchestrator.py:376-400`)
10. **Step 6: Persistence** — `EvaluationRepository.save_evaluation_result()` writes to `evaluation_results` table (`services/evaluation/orchestrator.py:446-451`)
11. **Response** — Returns full evaluation dict with scores, agent outputs, feedback (`services/evaluation/orchestrator.py:423-458`)

### Session Management Flow

1. **HTTP GET/POST** → `session_controller.*` routes (`controllers/session_controller.py`)
2. **Session CRUD** → `SessionService` → `SessionRepository` → PostgreSQL `evaluation_sessions` table
3. **Dashboard** → `RepositoryService.dashboard()` aggregates metrics across all sessions

### Report Generation Flow

1. **HTTP GET** → `report_controller.session_report()` or `repository_report()` (`controllers/report_controller.py:10,19`)
2. **Delegation** → `ReportService.generate()` spawns subprocess running `pdf_gen.py` (`services/report_service.py:15`)
3. **Response** → PDF file download via `send_file()`

**State Management:**
- Session state: `evaluation_sessions.status` — Active, Completed, Archived
- Repository evaluation state: `repositories.evaluation_status` — Pending, Evaluating, Completed, Failed
- Pipeline persistence: `evaluation_results` table with JSONB columns for agent outputs and criterion results
- Interrupted recovery: `RepositoryRepository.recover_interrupted()` resets `Evaluating` → `Pending` on startup (`services/container.py:24`)
- File-based caching: Each pipeline step writes to `evaluations/{session_id}/{repository_id}/{step}.json` for idempotency/recovery

## Key Abstractions

**BaseAgent (abstract):**
- Purpose: Contract for all evaluation agents — defines `run()`, `_write_output()`, `_validate_output()`
- Files: `services/evaluation/agent_base.py`
- Pattern: Template Method via ABC

**EvaluationOrchestrator:**
- Purpose: 6-step pipeline lifecycle manager — handles parallel execution, retries, step recovery, persistence
- Files: `services/evaluation/orchestrator.py`
- Pattern: Pipeline / Orchestrator

**ServiceContainer:**
- Purpose: Dependency injection composition root — wires all services together
- Files: `services/container.py`
- Pattern: DI Container (manual @dataclass)

**SnapshotBuilder:**
- Purpose: Assembles the `ProjectSnapshot` data structure from discovered files, metrics, metadata
- Files: `services/ingestion/snapshot_builder.py`
- Pattern: Builder

**Evidence Router:**
- Purpose: Pre-filters snapshot sections relevant to each rubric criterion (reduces LLM token usage)
- Files: `services/evaluation/evidence_router.py`
- Pattern: Routing / Strategy with map-based lookup

## Entry Points

**HTTP (via ASGI):**
- Location: `app.py:30` — `app = WsgiToAsgi(create_app())`
- Triggers: `uvicorn.run()` when executed directly (port 5001)
- Responsibilities: Flask app factory, Blueprint registration, service container initialization

**uvicorn server:**
- Location: `app.py:33-34`
- Triggers: `python app.py`
- Responsibilities: ASGI server for the Flask app

**CLI:**
- `scripts/migrate_to_postgres.py` — One-time SQLite → PostgreSQL migration

## Architectural Constraints

- **Threading:** Single-threaded event loop (ASGI). Pipeline uses `ThreadPoolExecutor(max_workers=2)` for parallel agent execution (`services/evaluation/orchestrator.py:179`). PDF generation spawns a subprocess via `subprocess.run()` (`services/report_service.py:21`).
- **Global state:** Application services stored in `flask.current_app.extensions["services"]` — request-scoped access via `services()` helper (`controllers/common.py:6`). Module-level logger instances throughout.
- **Database connections:** `psycopg.connect()` called per-operation via context manager (`with connect() as db:`) — no connection pooling configured.
- **Configuration-driven models:** `OllamaClient` reads model routing and timeout from environment variables (`OLLAMA_HOST`, `OLLAMA_PORT`, `OLLAMA_CODE_MODEL`, `OLLAMA_REASONING_MODEL`, `OLLAMA_TIMEOUT`).
- **No circular imports:** Controllers → Services → Repositories → Database. Services reference repositories by import; controllers reference services via `current_app.extensions`.

## Anti-Patterns

### Legacy table coexistence
**What happens:** The old `evaluations`, `evaluation_questions`, `evaluation_criteria` tables exist alongside the new `evaluation_results` table. The legacy `evaluations.hydrate()` method in `evaluation_repository.py` still references the old schema.
**Why it's wrong:** Dual-write/read confusion — some flows read from old tables while the pipeline writes to new ones.
**Do this instead:** Phase out old tables (migration_003_archive_old_tables.sql exists). Single-write, single-read path through `evaluation_results`.

### Subprocess PDF generation
**What happens:** `ReportService.generate()` calls `subprocess.run([sys.executable, "pdf_gen.py", ...])` (`services/report_service.py:21`).
**Why it's wrong:** Subprocess spawning is expensive, hard to debug, and blocks the request thread for up to 1800s. Error/return-code propagation is fragile.
**Do this instead:** In-process PDF generation using the same `reportlab` library directly, or async task queue.

### Ad-hoc connection management
**What happens:** Every repository method calls `with connect() as db:` independently — no transaction coordination across multiple repository calls in a single service operation.
**Why it's wrong:** Inconsistent state if intermediate operations fail (no rollback across repository calls).
**Do this instead:** Use a centralized transaction context manager or pass connections through service methods.

## Error Handling

**Strategy:** Hybrid — PEP 20-style exceptions for business logic errors, schema validation for LLM outputs, and try/except wrappers around external service calls.

**Patterns:**
- Custom Ollama exceptions: `OllamaConnectionError`, `OllamaModelNotFoundError`, `OllamaAPIError` (`services/ollama_client.py:22-54`)
- Schema validation fallback: Each agent has a fallback output when LLM output fails schema validation
- Orchestrator retry: `_run_agent_with_retry()` with configurable `max_retries=2` (`services/evaluation/orchestrator.py:148`)
- Pipeline partial failure: `pipeline_status` = "partial" + `failed_agents` list
- Repository status recovery: Interrupted evaluations reset to Pending on startup (`services/repository_repository.py:45-49`)

## Cross-Cutting Concerns

**Logging:** Standard `logging.getLogger(__name__)` throughout. No structured logging. Log level configured per-module.

**Validation:**
- JSON Schema (draft-07) validation of all LLM agent outputs (`jsonschema` library)
- Business validation (session status, rubric names, required fields) via `ValueError`/`LookupError` exceptions
- Environment variable validation via `RuntimeError` if `DATABASE_URL` is missing

**Authentication:** Flask `secret_key` hardcoded as "repo-eval-workflow" in `app.py:20`. No user authentication — single-user tool.

**Serialization:** JSON (via `json.dump` + `json.load`) for pipeline step caching. JSONB columns in PostgreSQL for agent outputs. `psycopg.types.json.Jsonb` adapter.

---

*Architecture analysis: 2026-07-13*
