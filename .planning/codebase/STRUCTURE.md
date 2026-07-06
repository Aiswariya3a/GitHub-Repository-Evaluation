# Codebase Structure

**Analysis Date:** 2026-07-06

## Directory Layout

```
GitHub-Repository-Evaluation/
├── controllers/         # Flask Blueprint route handlers (MVC Controller)
│   ├── __init__.py      # Re-exports all controllers
│   ├── common.py        # Shared helpers: services(), parse_evaluation(), session_context()
│   ├── evaluation_controller.py
│   ├── report_controller.py
│   ├── repository_controller.py
│   ├── rubric_controller.py
│   └── session_controller.py
├── database/            # PostgreSQL connection and schema
│   ├── __init__.py      # Re-exports connect(), initialize_database()
│   ├── postgres.py      # Connection factory, schema bootstrap
│   └── schema.sql       # Full DDL for all 16 tables
├── data/                # Legacy SQLite database (migration source)
│   └── evaluation_sessions.db
├── models/              # Domain data classes
│   ├── __init__.py      # Re-exports domain classes
│   └── domain.py        # EvaluationSession, Repository, Evaluation dataclasses
├── repositories/        # Data Access Layer — all SQL queries
│   ├── __init__.py      # Re-exports all repositories
│   ├── evaluation_repository.py
│   ├── repository_repository.py
│   ├── rubric_repository.py
│   └── session_repository.py
├── scripts/             # One-off migration scripts
│   └── migrate_to_postgres.py
├── services/            # Business Logic Layer
│   ├── __init__.py      # Re-exports all services
│   ├── analysis_service.py
│   ├── container.py     # ServiceContainer (dependency injection)
│   ├── evaluation_service.py
│   ├── github_service.py
│   ├── report_service.py
│   ├── repository_service.py
│   ├── rubric_service.py
│   └── session_service.py
├── static/              # Frontend static assets
│   ├── dashboard.css
│   └── styles.css
├── templates/           # Jinja2 server-side rendered templates
│   ├── analytics.html
│   ├── base.html        # Layout shell: sidebar nav, command palette, dialogs, toasts
│   ├── dashboard.html
│   ├── index.html
│   ├── overview.html
│   ├── reports.html
│   ├── repository_detail.html
│   ├── rubric_detail.html
│   ├── rubric_new.html
│   ├── rubrics.html
│   ├── session.html
│   └── settings.html
├── app.py               # Flask application factory + entry point
├── main.py              # CLI evaluation engine (subprocess target)
├── pdf_gen.py           # CLI PDF generator (subprocess target)
├── requirements.txt
├── .env                 # Environment variables (not committed)
├── example.env          # Environment variable template
├── .gitignore
├── repos/               # Git clone target directory (gitignored)
├── student_reports/     # Generated PDF output (gitignored)
├── repos.csv            # Input CSV — repository list
├── selected_repos.csv   # Input CSV — filtered repository list
├── evaluation_report.csv
├── plagiarism_report.csv
├── repo_report.csv
├── .agents/             # OpenCode agents (empty)
├── .planning/           # Planning documents
│   └── codebase/        # Codebase analysis documents (this directory)
├── README.md
├── README_UPDATE.md
├── START_HERE.md
├── ARCHITECTURE.md
├── RUBRIC_MAPPING.md
└── *.pdf                # Pre-existing consolidated/analysis PDFs
```

## Directory Purposes

**`controllers/`:**
- Purpose: HTTP route handlers — parse requests, delegate to services, return JSON or render templates
- Contains: 6 Python files (5 domain controllers + 1 common helpers)
- Key files:
  - `controllers/__init__.py` — Re-exports all 5 controller modules
  - `controllers/common.py` — `services()` accessor, `parse_evaluation()`, `session_context()` helper
  - `controllers/session_controller.py` — 6 page routes + 6 API routes for sessions
  - `controllers/rubric_controller.py` — 4 page routes + 7 API routes for rubrics

**`services/`:**
- Purpose: Business logic layer — orchestrates evaluation, report generation, GitHub interaction
- Contains: 9 Python files (7 service classes + container + init)
- Key files:
  - `services/container.py` — `ServiceContainer` dataclass with `build()` factory
  - `services/evaluation_service.py` — Subprocess management for `main.py`
  - `services/report_service.py` — Subprocess management for `pdf_gen.py`
  - `services/repository_service.py` — Largest service (68 lines), orchestrates repo lifecycle, dashboard, search

**`repositories/`:**
- Purpose: Data access — all PostgreSQL queries encapsulated in repository classes
- Contains: 5 Python files (4 repository classes + init)
- Key files:
  - `repositories/repository_repository.py` — Largest repository (99 lines), handles CRUD + dashboard + related data + search
  - `repositories/evaluation_repository.py` — Evaluation persistence with question/criteria/metadata sub-tables

**`database/`:**
- Purpose: Database connection management and schema
- Contains: `postgres.py` (connection factory), `schema.sql` (16-table DDL with indices)
- Note: Every connection is opened fresh via `psycopg.connect()` — no pooling

**`templates/`:**
- Purpose: Server-rendered HTML via Flask/Jinja2
- Contains: 12 templates
- Architecture: Single `base.html` layout with sidebar navigation, command palette (Ctrl+K), toast stack, and confirmation dialog. All other templates extend `base.html`.

**`models/`:**
- Purpose: Domain dataclasses for type hints and structured data
- Contains: `domain.py` with 3 frozen dataclasses: `EvaluationSession`, `Repository`, `Evaluation`
- Note: Models are currently only used for type annotation — actual data flows as PostgreSQL `dict_row` dictionaries

**`static/`:**
- Purpose: CSS stylesheets
- Contains: `styles.css` (main styles), `dashboard.css` (dashboard-specific styles)

## Key File Locations

**Entry Points:**
- `app.py:29` — Flask web application entry (debug mode, port 5000)
- `main.py:414` — CLI evaluation engine (invoked as subprocess)
- `pdf_gen.py:59` — CLI PDF report generator (invoked as subprocess)
- `scripts/migrate_to_postgres.py:119` — Legacy data migration script

**Configuration:**
- `.env` (not committed) — Environment variables: `DATABASE_URL`, `GITHUB_TOKEN`, `GEMINI_API_KEY`
- `example.env` — Template for required environment variables
- `app.py:19` — Flask secret key (hardcoded)
- `services/evaluation_service.py:42` — Subprocess timeout (1800s hardcoded)
- `repositories/rubric_repository.py` — Default rubric UUIDs hardcoded

**Core Business Logic:**
- `main.py` — Evaluation pipeline: clone, analyze, evaluate via Gemini, detect plagiarism (495 lines)
- `pdf_gen.py` — PDF report generation via ReportLab (440 lines)
- `services/repository_service.py` — Repository lifecycle orchestration (68 lines)
- `services/github_service.py` — GitHub API interaction and git clone (42 lines)

**Database Setup:**
- `database/schema.sql` — Complete DDL: 16 tables, indices, foreign keys, constraints (120 lines)
- `database/postgres.py` — Connection factory and schema auto-bootstrap (24 lines)

**Testing:**
- No test files detected in the project source (excluding virtual environment files)

## Naming Conventions

**Files:**
- Python source: `snake_case.py` — e.g., `repository_service.py`, `session_controller.py`
- Templates: `snake_case.html` — e.g., `rubric_detail.html`, `repository_detail.html`
- CSS: `snake_case.css` — e.g., `dashboard.css`, `styles.css`
- Init files: `__init__.py` in every package directory

**Directories:**
- Plural nouns for module groups: `controllers/`, `models/`, `repositories/`, `services/`, `templates/`, `scripts/`, `static/`, `data/`, `database/`

**Classes:**
- `PascalCase` service/repository/controller classes — e.g., `SessionService`, `RepositoryRepository`, `EvaluationController`
- Domain classes: `PascalCase` — `EvaluationSession`, `Repository`, `Evaluation`
- `ServiceContainer` — dataclass for DI

**Functions:**
- `snake_case` — `evaluate_pending()`, `get_session()`, `session_context()`, `parse_evaluation()`
- Static methods: `RepositoryService.added_code()` is a `@staticmethod`

**Variables:**
- `snake_case` — `session_id`, `repository_id`, `rubric_config`, `code_corpus`
- Single-letter loop vars: `i`, `row`, `item`

**Database:**
- Tables: `snake_case` plural — `evaluation_sessions`, `repositories`, `rubric_categories`, `evaluation_criteria`
- Columns: `snake_case` — `roll_number`, `repo_url`, `evaluation_status`, `rubric_version_id`
- Primary keys: `id` (UUID with `gen_random_uuid()`)
- Foreign keys: `{referenced_table}_id`

## Where to Add New Code

**New Feature (e.g., new analysis metric):**
1. Schema: Add table or column in `database/schema.sql`
2. Repository: Add query method to appropriate repository in `repositories/`
3. Service: Add orchestration method to appropriate service in `services/`
4. Controller: Add API route in appropriate controller in `controllers/`
5. Template: Add UI in appropriate template in `templates/`
6. Register blueprint: If new controller, register in `app.py:21-25`

**New Component/Module:**
- Implementation: Add file following existing naming in the appropriate layer directory
- Export: Add to the `__init__.py` of the layer
- Inject: If a new service, add to `ServiceContainer` dataclass and `build()` in `services/container.py`

**Utilities:**
- Shared helpers: Currently placed in `controllers/common.py`. For non-controller helpers, create `services/base_service.py` or a new `utils/` package

**Configuration:**
- New environment variable: Add to `example.env`, reference via `os.getenv()` at point of use
- New hardcoded defaults: Currently placed directly in the using file (consider moving to config module in future)

## Special Directories

**`data/`:**
- Purpose: Legacy SQLite database for migration
- Generated: No (legacy artifact from pre-PostgreSQL version)
- Committed: Yes (migration source)

**`repos/`:**
- Purpose: Git clone destination for student repositories during evaluation
- Generated: Yes (by `main.py` via `GitHubService.clone()`)
- Committed: No (gitignored)

**`student_reports/`:**
- Purpose: Output directory for per-student PDF reports before consolidation
- Generated: Yes (by `pdf_gen.py`)
- Committed: No (gitignored)

**`.planning/codebase/`:**
- Purpose: Codebase analysis documents consumed by GSD planning/execution tools
- Generated: Yes (by `/gsd-map-codebase` command)
- Committed: Yes

**.venv/ and venv/:**
- Purpose: Python virtual environment
- Generated: Yes (by `python -m venv`)
- Committed: No (gitignored)

---

*Structure analysis: 2026-07-06*
