# External Integrations

**Analysis Date:** 2026-07-13

## APIs & External Services

**GitHub REST API v3:**
- Used for: Repository metadata retrieval, commit history, contributor analysis, pull request/issue stats, repository existence/visibility checks
- Client: Custom `GitHubService` class in `services/github_service.py`
- Auth: Bearer token via `GITHUB_TOKEN` env var in HTTP `Authorization` header
- Rate limiting: No explicit client-side rate-limit handling (relies on GitHub's standard rate limits; unauthenticated requests have stricter limits)
- Endpoints used:
  - `GET /repos/{owner}/{repo}` — repo metadata (`services/github_service.py:31`)
  - `GET /repos/{owner}/{repo}/contents` — file listing for README detection (`services/github_service.py:60`)
  - `GET /repos/{owner}/{repo}/commits` — commit history with pagination (`services/github_service.py:74`)
  - `GET /repos/{owner}/{repo}/contributors` — contributor list (`services/github_service.py:117`)
  - `GET /repos/{owner}/{repo}/pulls` — pull requests with pagination (`services/github_service.py:146`)
  - `GET /repos/{owner}/{repo}/issues` — issues with pagination, PRs filtered out (`services/github_service.py:178`)

**Ollama API (local):**
- Used for: SLM (Small Language Model) inference for code evaluation, repository understanding, collaboration analysis, rubric evaluation, and feedback generation
- Client: Custom `OllamaClient` class in `services/ollama_client.py`
- Connection: HTTP on `OLLAMA_HOST:OLLAMA_PORT` (default `http://localhost:11434`)
- Endpoints used:
  - `GET /api/tags` — connectivity validation and model availability check (`ollama_client.py:122`)
  - `POST /api/generate` — inference with temperature=0, streaming disabled (`ollama_client.py:228-229`)
- Models:
  - `qwen2.5-coder:3b` — code understanding and repository analysis tasks ("code" role)
  - `phi-4-mini:3.8b` — collaboration/feedback/reasoning tasks ("reasoning" role)
- Custom exceptions: `OllamaConnectionError`, `OllamaModelNotFoundError`, `OllamaAPIError`

## Data Storage

**Databases:**

| Type | Provider | Connection | Client | Schema |
|------|----------|------------|--------|--------|
| Primary | PostgreSQL | `DATABASE_URL` env var | `psycopg` 3.2.9 (dict_row factory) | `database/schema.sql` (169 lines) |
| Legacy | SQLite | `data/evaluation_sessions.db` | `sqlite3` stdlib | Migrated to PostgreSQL via `scripts/migrate_to_postgres.py` |

**PostgreSQL Database Schema (`database/schema.sql`):**
- 18 tables total:
  - `rubrics`, `rubric_versions`, `rubric_categories`, `rubric_criteria` — Rubric management
  - `evaluation_sessions` — Evaluation session tracking
  - `repositories` — Repository records with GitHub metadata columns
  - `evaluations`, `evaluation_questions`, `evaluation_criteria` — Legacy evaluation tables (archived by migration 003)
  - `evaluation_results` — New pipeline evaluation results (JSONB storage for agent outputs)
  - `ingestion_records` — Snapshot storage (JSONB)
  - `code_quality`, `documentation`, `collaboration`, `project_health`, `technologies`, `contributors`, `commits`, `pull_requests`, `issues`, `files`, `evaluation_metadata` — Detailed repository metadata
  - `plagiarism_results` — Plagiarism similarity scores between repository pairs
- Extension: `pgcrypto` for `gen_random_uuid()`
- Indexes: 24 indexes across all tables for query performance

**Database Migrations:**
- `database/migration_001_ingestion.sql` — Adds `ingestion_records` table with GIN indexes on JSONB
- `database/migration_002_evaluation_results.sql` — Adds `evaluation_results` table for new pipeline
- `database/migration_003_archive_old_tables.sql` — Renames old evaluation tables to `_archive_` prefix

**File Storage:**
- Local filesystem only:
  - `repos/` — Cloned git repositories (`.gitignore`-listed)
  - `snapshots/` — Ingestion JSON snapshots
  - `evaluations/{session}/{repo}/` — Pipeline step output cache (idempotent recovery via JSON files)
  - `student_reports/` — Generated PDF reports (`.gitignore`-listed)
  - `archive/` — Archived data (`.gitignore`-listed)

**Caching:**
- Step output caching on local filesystem (`evaluations/{session_id}/{repository_id}/{step}.json`) — enables idempotent pipeline recovery per D-11/D-12
- No external caching service (Redis/Memcached)

## Authentication & Identity

**Auth Provider:**
- None (custom Flask secret key only)
- Implementation: `app.secret_key = "repo-eval-workflow"` in `app.py:20` — hardcoded string for Flask session cookies
- No user authentication, no login system, no multi-user support
- All API endpoints are unauthenticated

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Datadog, or similar)

**Logging:**
- Python `logging` module with `logging.getLogger(__name__)` throughout
- `INFO` level for production operations, `DEBUG` for detailed agent tracing
- No structured logging, no log aggregation, no log rotation configuration

**Health Checks:**
- `OllamaClient.validate_connectivity()` (`ollama_client.py:104`) — checks server reachability and model availability
- No application-level health endpoint exposed

## CI/CD & Deployment

**Hosting:**
- Not detected — no Dockerfile, docker-compose, `Procfile`, or deployment manifests found
- Designed to run locally with `uvicorn` on port 5001

**CI Pipeline:**
- None detected — no GitHub Actions, Jenkins, or other CI configuration

## Environment Configuration

**Required env vars:**
| Variable | Required | Default | Source |
|----------|----------|---------|--------|
| `DATABASE_URL` | Yes | — | `database/postgres.py:11` |
| `GITHUB_TOKEN` | Yes (for API) | `""` | `services/github_service.py:11` |
| `OLLAMA_HOST` | No | `http://localhost` | `services/ollama_client.py:70` |
| `OLLAMA_PORT` | No | `11434` | `services/ollama_client.py:71` |
| `OLLAMA_TIMEOUT` | No | `300` | `services/ollama_client.py:75` |
| `OLLAMA_CODE_MODEL` | No | `qwen2.5-coder:3b` | `services/ollama_client.py:83` |
| `OLLAMA_REASONING_MODEL` | No | `phi-4-mini:3.8b` | `services/ollama_client.py:84` |

**Secrets location:**
- `.env` file at project root (listed in `.gitignore`)
- `GITHUB_TOKEN` stored in `.env` — loaded via `python-dotenv`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Service Architecture Map

```
┌─────────────────────┐      ┌──────────────────────┐
│     Flask App        │      │    Ollama Server      │
│   (app.py:5001)      │─────▶│  (localhost:11434)    │
│                      │ HTTP │  qwen2.5-coder:3b     │
│  OllamaClient         │◀────│  phi-4-mini:3.8b      │
└──────────┬───────────┘      └──────────────────────┘
           │
           │ HTTP
           ▼
┌──────────────────────┐
│   GitHub API v3       │
│  api.github.com       │
│  (GITHUB_TOKEN auth)  │
└──────────────────────┘

┌──────────────────────┐
│   PostgreSQL          │
│  DATABASE_URL         │
│  (psycopg 3.2.9)     │
└──────────────────────┘

Local Filesystem:
├── repos/              (git clones)
├── snapshots/          (ingestion cache)
├── evaluations/        (step output cache)
└── student_reports/    (PDF output)
```

---

*Integration audit: 2026-07-13*
