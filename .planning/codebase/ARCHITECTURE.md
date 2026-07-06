<!-- refreshed: 2026-07-06 -->
# Architecture

**Analysis Date:** 2026-07-06

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│  Flask Templates (server-side rendered HTML) + Jinja2 + CSS         │
│  `templates/`  `static/`  `controllers/`                            │
├──────────────────┬──────────────────┬───────────────────────────────┤
│   Session UI     │  Dashboard       │  Rubric Config / Reports      │
│  `session_ctrl`  │  `overview.html` │  `rubric_ctrl` `report_ctrl`  │
└────────┬─────────┴────────┬─────────┴──────────┬────────────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                                  │
│  Business logic, orchestration, AI evaluation                       │
│  `services/`                                                        │
│                                                                     │
│  ┌────────────┐ ┌──────────────┐ ┌────────────────┐                │
│  │  Session   │ │ Repository   │ │  Evaluation    │                │
│  │  Service   │ │ Service      │ │  Service       │                │
│  └─────┬──────┘ └──────┬───────┘ └───────┬────────┘                │
│  ┌──────┴──────┐ ┌─────┴────────┐ ┌──────┴─────────┐               │
│  │  Rubric    │ │  Analysis    │ │  Report        │                │
│  │  Service   │ │  Service     │ │  Service       │                │
│  └─────┬──────┘ └──────┬───────┘ └───────┬────────┘                │
│  ┌──────┴──────┐                        │                          │
│  │  GitHub     │                        │                          │
│  │  Service    │                        │                          │
│  └─────────────┘                        │                          │
└─────────────────────────────────────────┼──────────────────────────┘
                                          │
              ┌───────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    REPOSITORY LAYER (Data Access)                    │
│  `repositories/`                                                    │
│  ┌────────────┐ ┌──────────────┐ ┌────────────────┐                │
│  │  Session   │ │ Repository   │ │  Evaluation    │                │
│  │  Repo      │ │ Repo         │ │  Repo          │                │
│  └─────┬──────┘ └──────┬───────┘ └───────┬────────┘                │
│  ┌──────┴──────┐                          │                         │
│  │  Rubric     │                          │                         │
│  │  Repo       │                          │                         │
│  └─────────────┘                          │                         │
└───────────────────────────────────────────┼─────────────────────────┘
                                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYER                              │
│  PostgreSQL via psycopg 3 (connection-per-query pattern)            │
│  `database/postgres.py`  `database/schema.sql`                     │
└─────────────────────────────────────────────────────────────────────┘

EXTERNAL:
┌──────────────┐   ┌──────────────────┐   ┌─────────────────────────┐
│  GitHub API  │   │  Google Gemini   │   │  Git (clone via         │
│  REST v3     │   │  2.5 Flash       │   │  subprocess)            │
└──────────────┘   └──────────────────┘   └─────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Flask App Factory | Creates Flask app, registers blueprints, injects ServiceContainer | `app.py` |
| Evaluation Engine | CLI batch evaluator (main.py) — clones, analyzes, evaluates, detects plagiarism | `main.py` |
| PDF Generator | Generates individual + consolidated PDF reports via ReportLab | `pdf_gen.py` |
| SessionController | Session CRUD endpoints, page routes | `controllers/session_controller.py` |
| RepositoryController | Repository CRUD, search API | `controllers/repository_controller.py` |
| EvaluationController | Triggers evaluation pipelines | `controllers/evaluation_controller.py` |
| ReportController | PDF download endpoints | `controllers/report_controller.py` |
| RubricController | Rubric CRUD, version management | `controllers/rubric_controller.py` |
| ServiceContainer | Dependency injection hub for all services | `services/container.py` |
| SessionService | Session lifecycle management | `services/session_service.py` |
| RepositoryService | Repository orchestration, dashboard metrics, search | `services/repository_service.py` |
| EvaluationService | Spawns `main.py` as subprocess for evaluation | `services/evaluation_service.py` |
| AnalysisService | Delta code detection, evaluation result persistence | `services/analysis_service.py` |
| GitHubService | GitHub API interaction, repo cloning | `services/github_service.py` |
| ReportService | Spawns `pdf_gen.py` as subprocess for PDF generation | `services/report_service.py` |
| RubricService | Rubric CRUD, versioning, default rubric | `services/rubric_service.py` |

## Pattern Overview

**Overall:** Layered architecture with Controller → Service → Repository → Database separation. Uses Flask Blueprints for modular HTTP routing.

**Key Characteristics:**
- Controllers contain no business logic — they parse requests, delegate to services, and return responses
- Services orchestrate business rules and cross-cutting concerns
- Repositories encapsulate all database queries with connection-per-call pattern
- Heavy evaluation tasks (`main.py`, `pdf_gen.py`) run as subprocesses spawned by services
- ServiceContainer provides explicit dependency injection at app bootstrap

## Layers

**Presentation Layer:**
- Purpose: HTTP interfaces and server-rendered HTML views
- Location: `controllers/`, `templates/`, `static/`
- Contains: 5 Flask Blueprint controllers, 12 Jinja2 templates, 2 CSS files
- Depends on: Service Layer (via `current_app.extensions["services"]`)
- Used by: End users via browser

**Service Layer:**
- Purpose: Business logic, evaluation orchestration, AI integration
- Location: `services/`
- Contains: 7 service classes, 1 dependency injection container
- Depends on: Repository Layer
- Used by: Presentation Layer (controllers)

**Repository Layer (Data Access):**
- Purpose: All database queries, result marshalling
- Location: `repositories/`
- Contains: 4 repository classes
- Depends on: Database Layer (`database/postgres.py`)
- Used by: Service Layer

**Database Layer:**
- Purpose: PostgreSQL connection management, schema initialization
- Location: `database/`
- Contains: Connection factory (`postgres.py`), schema DDL (`schema.sql`)
- Depends on: `psycopg` library
- Used by: Repository Layer

**External Integrations Layer:**
- Purpose: Third-party API and tool interactions
- Location: `services/github_service.py`, `main.py`
- Contains: GitHub REST API client, Git subprocess calls, Google Gemini AI client
- Depends on: `requests`, `google.generativeai`, system `git`

## Data Flow

### Primary Request Path: Session Evaluation

1. HTTP POST `/api/sessions/<id>/evaluate` — `controllers/evaluation_controller.py:13`
2. Validates session is "Active" via `SessionService.get_session()` (`services/session_service.py:25`)
3. `EvaluationService.evaluate_pending()` (`services/evaluation_service.py:20`) marks repos as "Evaluating", spawns `main.py --session-id <id>` as subprocess
4. `main.py` loads session repos from DB, clones each repo via `GitHubService` (`services/github_service.py`), reads code, computes delta via `AnalysisService.added_code()` (`services/analysis_service.py:5`), evaluates via Google Gemini (`main.py:evaluate_code()` at line 141)
5. Results saved to PostgreSQL via `RepositoryService.save_repository_evaluation()` -> `EvaluationRepository.save()` (`repositories/evaluation_repository.py:48`)
6. Plagiarism detection runs: TF-IDF vectorization + cosine similarity across all repos (`main.py:472-493`)
7. Results saved via `AnalysisService.save_plagiarism()` -> `EvaluationRepository.save_plagiarism()` (`repositories/evaluation_repository.py:72`)

### Report Generation Flow

1. HTTP GET `/sessions/<id>/report` — `controllers/report_controller.py:10`
2. `ReportService.generate()` (`services/report_service.py:15`) spawns `pdf_gen.py --session-id <id>` as subprocess
3. `pdf_gen.py` loads completed evaluations from DB, generates individual student PDFs via ReportLab, then merges all PDFs into `Final_Consolidated_Report.pdf` using PyPDF2 (`pdf_gen.py:427-439`)
4. Result streamed to browser as attachment

### Dashboard Data Flow

1. HTTP GET `/api/dashboard` — `controllers/session_controller.py:44`
2. `RepositoryService.dashboard()` (`services/repository_service.py:43`) queries 6 aggregated metric sets from PostgreSQL
3. Returns JSON with metrics, recent activity, leaderboard, score distribution, technologies

### Search Flow

1. HTTP GET `/api/search?q=query` — `controllers/repository_controller.py:8`
2. `RepositoryService.search()` (`services/repository_service.py:65`) queries sessions and repositories via ILIKE patterns
3. Returns JSON results for command palette UI

**State Management:**
- All evaluation state stored in PostgreSQL (sessions, repositories, evaluations, plagiarism results)
- Short-lived temp directories used for git clones and PDF generation, cleaned up after use
- Flask session secret key hardcoded in `app.py:19` (`"repo-eval-workflow"`)

## Key Abstractions

**ServiceContainer:**
- Purpose: Explicit dependency injection for all services
- Location: `services/container.py`
- Pattern: Dataclass with `@classmethod build()` factory
- Initializes services in dependency order: RubricService → SessionService → RepositoryService → EvaluationService → ReportService
- Injected into Flask app via `app.extensions["services"]` at `app.py:20`

**Blueprint + Controller Class:**
- Purpose: Each domain area exposes a Flask Blueprint instance and a wrapper class
- Examples: `controllers/session_controller.py` (blueprint + SessionController class), `controllers/repository_controller.py`
- Pattern: Module-level blueprint for route registration, class with `blueprint` attribute for clean import in `app.py`

**Repository + Service Separation:**
- Purpose: Database queries isolated in repositories, orchestration in services
- Examples: `SessionService` (`services/session_service.py`) delegates to `SessionRepository` (`repositories/session_repository.py`)
- Pattern: Services own the lifecycle; repositories own SQL

**Subprocess Evaluation:**
- Purpose: Heavy AI evaluation and PDF generation run as detached subprocesses with temp workspaces
- Examples: `EvaluationService.evaluate_pending()` spawns `main.py`, `ReportService.generate()` spawns `pdf_gen.py`
- Pattern: Services manage temp directories, timeouts, and error propagation from subprocess exit codes

## Entry Points

**Web Application:**
- Location: `app.py:29` — `app = create_app()`
- Triggers: `flask run` or `python app.py` (debug on port 5000)
- Responsibilities: Blueprint registration, service container bootstrap

**CLI Evaluation Engine:**
- Location: `main.py`
- Triggers: Spawned by `EvaluationService.evaluate_pending()` via subprocess with `--session-id` argument
- Responsibilities: Clone repos, read code, evaluate via AI, save results, detect plagiarism

**PDF Report Generator:**
- Location: `pdf_gen.py`
- Triggers: Spawned by `ReportService.generate()` via subprocess with `--session-id` argument
- Responsibilities: Load evaluations, generate individual PDFs, produce consolidated report

**Database Migration:**
- Location: `scripts/migrate_to_postgres.py`
- Triggers: Manual execution via `python scripts/migrate_to_postgres.py`
- Responsibilities: One-time migration from legacy SQLite store to PostgreSQL

## Architectural Constraints

- **Threading:** Flask dev server is single-threaded by default. Evaluation runs are protected by `_evaluation_lock` (threading.Lock) in `services/evaluation_service.py:12` to prevent concurrent `main.py` executions per session.
- **Global state:** Module-level lock `_evaluation_lock` in `services/evaluation_service.py:12` is the primary global state. ServiceContainer is per-request via `app.extensions["services"]`.
- **Circular imports:** Avoided via deferred imports. `app.py` imports controllers and ServiceContainer after `load_dotenv()`. Services import repositories at module level (no circular chains).
- **Subprocess isolation:** Evaluation and PDF generation run in subprocesses, not in the main Flask process, preventing GIL contention and process crashes from affecting the web server.
- **Connection-per-call:** Every database operation opens and closes its own PostgreSQL connection via `database/postgres.py:18` — no connection pooling.
- **Score clamping:** All AI evaluation scores are clamped to rubric maximums in `main.py:346` to prevent LLM over-scoring.

## Anti-Patterns

### Hardcoded Config in Application Code

**What happens:** Hardcoded Flask secret key (`app.py:19`: `"repo-eval-workflow"`), GitHub token header construction (`services/github_service.py:11`), and timeout values (`services/evaluation_service.py:42`: 1800s) exist directly in source files.
**Why it's wrong:** Secret key should come from environment; token construction assumes token format; timeouts should be configurable.
**Do this instead:** Use `os.getenv("FLASK_SECRET_KEY")` in `app.py:19` with a fallback that warns in development.

### Connection-per-Call Database Access

**What happens:** Every repository method calls `with connect() as db:` to open a new PostgreSQL connection (`repositories/repository_repository.py:6`, `repositories/session_repository.py:7`, etc.).
**Why it's wrong:** No connection pooling — each query creates/tears down a TCP connection, adding ~50ms latency per call. Dashboard endpoints making 6+ queries incur significant overhead.
**Do this instead:** Use `psycopg_pool.ConnectionPool` (`psycopg_pool` package) or create a module-level connection pool in `database/postgres.py`.

### Flask Secret Key Exposed in Source

**What happens:** `app.py:19` — `app.secret_key = "repo-eval-workflow"` is a hardcoded string committed to version control.
**Why it's wrong:** Flask uses this for session signing. A known key allows session forgery. Not suitable for production.
**Do this instead:** Load from environment: `os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())`.

### Mixed Concerns in Repository Layer

**What happens:** `RepositoryRepository` (`repositories/repository_repository.py`) handles repository CRUD, dashboard metrics (6-table joins), related data queries (10 tables individually queried), and search — all in a single class with 99 lines.
**Why it's wrong:** Violates Single Responsibility Principle. Dashboard method alone returns 6 different result sets. Makes testing and maintenance harder.
**Do this instead:** Split into `DashboardRepository`, `SearchRepository`, or use query objects.

### Rubric Evaluation Logic Duplicated

**What happens:** `main.py` has two evaluation code paths — `evaluate_code()` (lines 141–361) and `evaluate_code_dynamic()` (lines 364–408) — that differ mainly in prompt construction and schema handling but share the same AI call, JSON parsing, and score clamping logic.
**Why it's wrong:** Code duplication of ~50 lines. Any fix to one function must be applied to both.
**Do this instead:** Extract shared evaluation flow into a common method or a separate `EvaluationEngine` class.

## Error Handling

**Strategy:** Controllers catch `ValueError`, `LookupError`, and `PermissionError` for known failure modes, returning JSON error responses with appropriate HTTP status codes. Unexpected exceptions propagate as 500 with JSON error body.

**Patterns:**
- Controller methods wrap service calls in try/except with domain-specific exception types (`controllers/evaluation_controller.py:17`, `controllers/rubric_controller.py:29`)
- `EvaluationService` catches subprocess failures and marks repositories as Failed via `repositories.mark_failed()` (`services/evaluation_service.py:48`)
- `main.py` evaluation handles Gemini API exceptions at `main.py:360` returning `{"error": "JSON parsing failed"}`
- `session_context()` helper (`controllers/common.py:20`) calls `abort(404)` for missing sessions

## Cross-Cutting Concerns

**Logging:** Console-based `print()` statements throughout (`services/evaluation_service.py:35`, `main.py:417`, `pdf_gen.py:317`). No structured logging (no `logging` module usage detected in project code).
**Validation:** Input validation is minimal — controller methods perform basic type coercion and strip. Session name and rubric name checked for emptiness. No schema validation library used.
**Authentication:** None. No login, no auth middleware, no API keys. Application assumes trusted network.
**CORS:** Not configured. Flask dev server serves same-origin.

---

*Architecture analysis: 2026-07-06*
