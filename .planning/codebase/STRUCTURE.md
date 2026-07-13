# Codebase Structure

**Analysis Date:** 2026-07-13

## Directory Layout

```
GitHub-Repository-Evaluation/
├── app.py                          # Flask app factory, ASGI entry point
├── pdf_gen.py                      # PDF generation script (subprocess target)
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Pytest configuration
├── AGENTS.md                       # AI attribution
├── example.env                     # Environment variable template
├── README.md                       # Project README
├── ARCHITECTURE.md                 # Architecture documentation
│
├── controllers/                    # HTTP route handlers (Flask Blueprints)
│   ├── __init__.py                 # Barrel exports
│   ├── common.py                   # services() accessor, helper functions
│   ├── session_controller.py       # Sessions CRUD + page routes
│   ├── repository_controller.py    # Repositories CRUD + search
│   ├── evaluation_controller.py    # Evaluate/reevaluate endpoints
│   ├── report_controller.py        # PDF download endpoints
│   └── rubric_controller.py        # Rubric CRUD + versioning
│
├── services/                       # Business logic layer
│   ├── __init__.py                 # Barrel exports
│   ├── container.py                # ServiceContainer (DI composition root)
│   ├── session_service.py          # Session lifecycle
│   ├── repository_service.py       # Repository lifecycle + hydration
│   ├── github_service.py           # GitHub API: clone, metadata
│   ├── ingestion_service.py        # Ingestion pipeline (9 stages)
│   ├── rubric_service.py           # Rubric version management
│   ├── report_service.py           # PDF generation via subprocess
│   ├── analysis_service.py         # Legacy analysis wrapper
│   ├── ollama_client.py            # Ollama HTTP client for SLM inference
│   │
│   ├── evaluation/                 # Multi-agent evaluation pipeline
│   │   ├── __init__.py             # Barrel exports
│   │   ├── agent_base.py           # BaseAgent abstract class
│   │   ├── orchestrator.py         # EvaluationOrchestrator (6-step pipeline)
│   │   ├── pipeline_service.py     # PipelineService (high-level entry)
│   │   ├── schemas.py              # JSON Schema definitions (draft-07)
│   │   ├── ollama_router.py        # System prompt templates
│   │   ├── evidence_router.py      # Category→evidence section routing
│   │   ├── score_aggregator.py     # Deterministic score aggregation
│   │   ├── repo_understanding_agent.py    # Capability agent 1
│   │   ├── code_understanding_agent.py    # Capability agent 2
│   │   ├── collaboration_agent.py         # Capability agent 3
│   │   ├── rubric_evaluation_agent.py     # Per-criterion evaluator
│   │   └── feedback_agent.py              # Feedback generator
│   │
│   └── ingestion/                  # Repository ingestion pipeline
│       ├── __init__.py             # Barrel exports
│       ├── file_discoverer.py      # File discovery + language detection
│       ├── code_parser.py          # AST-based code parsing (multi-language)
│       ├── metrics_calculator.py   # Code metrics computation
│       ├── delta_detector.py       # Student vs template diff detection
│       └── snapshot_builder.py     # ProjectSnapshot assembly
│
├── repositories/                   # PostgreSQL data access layer
│   ├── __init__.py                 # Barrel exports
│   ├── session_repository.py       # evaluation_sessions CRUD
│   ├── repository_repository.py    # repositories CRUD + dashboard queries
│   ├── evaluation_repository.py    # evaluation_results persistence
│   ├── ingestion_repository.py     # ingestion_records CRUD
│   └── rubric_repository.py        # rubrics + versions + categories + criteria
│
├── database/                       # Database configuration and schema
│   ├── __init__.py
│   ├── postgres.py                 # Connection factory + DB init
│   ├── schema.sql                  # Full DDL (19+ tables with indexes)
│   ├── migration_001_ingestion.sql     # ingestion_records table
│   ├── migration_002_evaluation_results.sql  # evaluation_results table
│   └── migration_003_archive_old_tables.sql  # Legacy cleanup script
│
├── models/                         # Domain types (dataclasses)
│   ├── __init__.py                 # Barrel exports
│   ├── domain.py                   # EvaluationSession, Repository
│   ├── evaluation_models.py        # CriterionEvaluation, CategoryScore, AggregatedScore
│   └── ingestion_models.py         # ProjectSnapshot, delta types, file types
│
├── controllers/__init__.py         # (listed above with controllers/)
│
├── templates/                      # Jinja2 HTML templates (Flask)
│   ├── base.html                   # Base layout
│   ├── overview.html               # Dashboard overview
│   ├── dashboard.html              # Sessions list page
│   ├── session.html                # Single session detail
│   ├── repository_detail.html      # Single repository detail
│   ├── reports.html                # Reports page
│   ├── analytics.html              # Analytics page
│   ├── settings.html               # Settings page
│   ├── rubrics.html                # Rubric list page
│   ├── rubric_new.html             # Create rubric page
│   └── rubric_detail.html          # Rubric detail page
│
├── static/                         # Static assets
│   ├── styles.css                  # Main stylesheet
│   └── dashboard.css               # Dashboard-specific styles
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Shared fixtures (mock Ollama, sample data)
│   ├── test_orchestrator.py        # EvaluationOrchestrator unit tests
│   ├── test_agents.py              # Agent unit tests
│   ├── test_schemas.py             # Schema validation tests
│   ├── test_evidence_router.py     # Evidence routing tests
│   ├── test_score_aggregator.py    # Score aggregation tests
│   ├── test_pipeline_service.py    # PipelineService tests
│   └── test_integration.py         # Integration tests (marked @integration)
│
├── config/                         # Configuration data
│   └── extensions.json             # Language extension → parser mapping
│
├── scripts/                        # Utility scripts
│   └── migrate_to_postgres.py      # SQLite → PostgreSQL migration
│
├── snapshots/                      # Generated ingestion JSON snapshots
│   └── *_snapshot.json             # (output directory, gitignored?)
│
├── evaluations/                    # Pipeline step cache (created at runtime)
│
├── repos/                          # Cloned repositories (created at runtime)
│
├── data/                           # SQLite source for migration (legacy)
│
├── student_reports/                # Generated PDF reports (output)
│
├── .planning/                      # GSD planning artifacts
│   └── codebase/                   # Architecture mapping documents
│
├── archive/                        # Archived/backup files
│
├── .venv/                          # Python virtual environment (gitignored)
└── .git/                           # Git repository
```

## Directory Purposes

**`controllers/`:**
- Purpose: HTTP request/response handling via Flask Blueprints
- Contains: 6 controller modules, each with a Blueprint instance and a class wrapper
- Key files: `common.py:6` (`services()` accessor) — the single point of entry to the service layer from controllers

**`services/`:**
- Purpose: All business logic — session/repo workflows, external integrations, evaluation pipeline, ingestion pipeline
- Contains: 8 top-level service modules + 2 sub-packages (`evaluation/`, `ingestion/`)
- Key files: `container.py` — the DI composition root wired in `app.py`

**`services/evaluation/`:**
- Purpose: Multi-agent SLM evaluation pipeline — agents, orchestrator, schemas, routing, aggregation
- Contains: 5 agents, orchestrator, pipeline service, evidence router, score aggregator, schemas, system prompts
- Key files: `orchestrator.py` — the 6-step pipeline manager; `agent_base.py` — abstract agent contract

**`services/ingestion/`:**
- Purpose: Repository ingestion pipeline — clone, discover, parse, metric, delta, snapshot
- Contains: FileDiscoverer, CodeParser, MetricsCalculator, DeltaDetector, SnapshotBuilder
- Key files: `file_discoverer.py` — language detection via `config/extensions.json`

**`repositories/`:**
- Purpose: PostgreSQL data access — each repository class wraps queries for one table group
- Contains: 5 repository classes, each with CRUD and specialized queries
- Key files: `repository_repository.py` — most complex, with dashboard aggregation queries and `recover_interrupted()`

**`models/`:**
- Purpose: Pure domain types as frozen/mutable `@dataclass` instances
- Contains: 3 modules with ~20 dataclass definitions
- Key files: `ingestion_models.py` — largest, defines ProjectSnapshot and all nested delta types

**`database/`:**
- Purpose: PostgreSQL connection management, schema DDL, incremental migrations
- Contains: Connection factory, full schema, 3 migration files
- Key files: `postgres.py` — `connect()` factory and `initialize_database()`; `schema.sql` — 169 lines of DDL with indexes

**`templates/`:**
- Purpose: Jinja2 HTML templates rendered by Flask controllers
- Contains: 12 templates — base layout, pages for sessions, repositories, rubrics, reports, analytics
- Key files: `base.html`, `session.html`, `repository_detail.html`

**`tests/`:**
- Purpose: Test suite with shared fixtures, unit tests, and integration tests
- Contains: 8 test files with `conftest.py` as the fixture hub
- Key files: `conftest.py` — mock Ollama, sample snapshots, sample rubrics; `test_orchestrator.py` — 460 lines of pipeline tests

## Key File Locations

**Entry Points:**
- `app.py`: Flask app factory `create_app()` + ASGI `WsgiToAsgi` wrapper + `uvicorn.run()` entry
- `app.py:30`: `app = WsgiToAsgi(create_app())` — the module-level ASGI app instance

**Configuration:**
- `config/extensions.json`: Language extension → parser/comment-syntax mapping for file discovery
- `example.env`: Template for environment variables
- `app.py:7`: `load_dotenv()` loads `.env` at startup
- `pytest.ini`: Pytest markers (integration) and test paths
- `requirements.txt`: Full dependency list with pinned versions

**Core Logic:**
- `services/evaluation/orchestrator.py`: The 459-line orchestrator — the heart of the evaluation pipeline
- `services/ingestion_service.py`: 9-stage ingestion pipeline (clone → persist)
- `services/github_service.py`: GitHub API integration (clone, metadata, commits, PRs, issues)
- `services/ollama_client.py`: HTTP client for Ollama SLM with model routing

**Testing:**
- `tests/conftest.py`: Fixtures for mock Ollama, sample snapshots, sample rubrics
- `tests/test_orchestrator.py`: 460-line comprehensive orchestrator tests

## Naming Conventions

**Files:**
- Python files: `snake_case.py` — descriptive names for modules (`session_controller.py`, `evaluation_repository.py`)
- Sub-packages: Single word for domain grouping (`evaluation/`, `ingestion/`, models in `models/`)
- Test files: `test_<module_name>.py` — mirrors source structure (`test_orchestrator.py`, `test_agents.py`)
- HTML templates: Descriptive lowercase (`session.html`, `repository_detail.html`)

**Directories:**
- All lowercase, plural nouns: `controllers/`, `services/`, `repositories/`, `models/`, `templates/`, `tests/`
- Domain subdirectories: `services/evaluation/`, `services/ingestion/`
- Output directories: `snapshots/`, `student_reports/`, `repos/` (runtime-created)

**Classes:**
- PascalCase with Domain suffix: `SessionService`, `RepositoryController`, `EvaluationOrchestrator`
- Abstract base: `BaseAgent`
- Agent suffix for pipeline agents: `RepoUnderstandingAgent`, `CodeUnderstandingAgent`, `CollaborationAgent`, `RubricEvaluationAgent`, `FeedbackAgent`
- Repository suffix for persistence classes: `SessionRepository`, `RepositoryRepository`

**Functions/Methods:**
- `snake_case` — descriptive verbs: `evaluate_session_repositories()`, `add_repositories()`, `save_evaluation_result()`
- Private methods prefixed with underscore: `_hydrate()`, `_run_agent_with_retry()`, `_build_file_summary()`
- Static methods: `_normalize_output()` on agent classes

**Models/Dataclasses:**
- PascalCase: `EvaluationSession`, `ProjectSnapshot`, `AggregatedScore`, `CriterionEvaluation`

## Where to Add New Code

**New Feature (e.g., new capability agent):**
- Primary code: Create new agent class in `services/evaluation/` extending `BaseAgent`
- Register in `services/evaluation/__init__.py` barrel export
- Wire into orchestrator: Add agent instance in `EvaluationOrchestrator.__init__()` and add step in `evaluate()` method
- Tests: Create `tests/test_<agent_name>.py` using fixtures from `conftest.py`

**New API Endpoint:**
- Implementation: Add route function in the appropriate `controllers/<domain>_controller.py`
- Business logic: Add or use existing service method in `services/<domain>_service.py`
- Persistence: Add or use existing repository method in `repositories/<domain>_repository.py`

**New Template/Page:**
- Template: Add HTML file to `templates/`
- Route: Add GET route in `controllers/session_controller.py` (or appropriate controller)
- Static assets: Add CSS to `static/styles.css` or `static/dashboard.css`

**New Database Table:**
- DDL: Add CREATE TABLE to `database/schema.sql` or create a new `database/migration_NNN_*.sql`
- Access: Add new repository class in `repositories/` or add methods to existing repository
- Connection: Use `with connect() as db:` pattern from `database/postgres.py`

**New Service:**
- Implementation: Create file in `services/`
- Wire into DI: Add to `ServiceContainer` in `services/container.py` and update `ServiceContainer.build()`
- Export: Add to `services/__init__.py` barrel

**New Integration (external API):**
- Client: Create service class in `services/` (e.g., pattern of `GitHubService`, `OllamaClient`)
- Config: Add environment variables, document in `example.env`
- Injection: Wire through `ServiceContainer` or pass as constructor dependency

## Special Directories

**`snapshots/`:**
- Purpose: Generated ingestion JSON snapshot files
- Generated: Yes (by `IngestionService.ingest()`)
- Committed: Partial — existing snapshots appear to be checked in; new ones generated at runtime

**`evaluations/`:**
- Purpose: Pipeline step cache files (`{session}/{repo}/{step}.json`) for idempotency
- Generated: Yes (by `EvaluationOrchestrator`)
- Committed: No (runtime output)

**`repos/`:**
- Purpose: Cloned GitHub repositories (temporary, cleaned after ingestion)
- Generated: Yes (by `GitHubService.clone()`)
- Committed: No (cleaned in `IngestionService.ingest()` finally block)

**`student_reports/`:**
- Purpose: Generated PDF reports (output of `pdf_gen.py`)
- Generated: Yes (by `pdf_gen.py` via `ReportService`)
- Committed: No (runtime output)

**`data/`:**
- Purpose: Legacy SQLite database source for migration
- Generated: No (legacy artifact)
- Committed: Yes

**`.planning/`:**
- Purpose: GSD workflow planning artifacts — milestones, phases, state, codebase maps
- Generated: Yes (by GSD commands)
- Committed: Yes

---

*Structure analysis: 2026-07-13*
