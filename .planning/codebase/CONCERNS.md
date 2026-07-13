# Codebase Concerns

**Analysis Date:** 2026-07-13

## Tech Debt

### Hardcoded Flask Secret Key in Production
- **Issue:** `app.py` hardcodes `app.secret_key = "repo-eval-workflow"` as a literal string (line 20). This is insecure for any deployment — Flask uses this key for signing session cookies and flash messages. An attacker who knows this value can forge session cookies.
- **Files:** `app.py:20`
- **Impact:** Session forgery, CSRF token compromise, potential privilege escalation.
- **Fix approach:** Read `SECRET_KEY` from environment variable with a fallback for development only:
  ```python
  app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())
  ```
  Warn (not silently fallback) if environment variable is missing in non-dev mode.

### Bare `except:` Clauses Throughout Controllers
- **Issue:** Multiple controller endpoints wrap entire handler bodies in bare `except Exception as exc: return jsonify(error=str(exc)), 500` blocks. This swallows all exceptions indiscriminately including `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` (though the `as exc` pattern does at least keep `BaseException` separate). More critically, it leaks internal error details to API clients.
- **Files:**
  - `controllers/evaluation_controller.py:27,42,54`
  - `controllers/report_controller.py:15,23`
  - `controllers/common.py:36`
- **Impact:** Internal server errors always return 500 with the exception message exposed to the caller. No logging of stack traces occurs.
- **Fix approach:** Replace with structured error handling:
  ```python
  except Exception as exc:
      logger.exception("Evaluation failed for session %s", session_id)
      return jsonify(error="An internal error occurred."), 500
  ```

### Silent Exception Swallowing in Service Layer
- **Issue:** Multiple service methods use bare `except: pass` or `except Exception: pass` patterns, silently discarding errors without logging.
- **Files:**
  - `services/github_service.py:50-51,61,79,110-111,139-140,171-172,202-203,222-223` — nearly every GitHub API method catches `Exception` and returns empty/default values with no logging
  - `services/ingestion_service.py:82-83,127-128,165-166` — catches and silently ignores errors during metadata fetch, file parsing, delta detection
  - `services/repository_service.py:87-88,93-94,96-98` — catches and ignores errors during repository detail hydration
  - `database/postgres.py:31` — migration execution silently ignores failures
- **Impact:** Errors silently disappear, making debugging extremely difficult. A broken GitHub API call, corrupt ingestion record, or failed migration could go unnoticed for days.
- **Fix approach:** Add at minimum `logger.warning()` or `logger.exception()` before `pass` in non-critical paths. For data-critical paths, re-raise or explicitly handle.

### Abandoned `archive/` Directory Contains Old Gemini-Based Evaluation Code
- **Issue:** `archive/main.py` (496 lines) references `GEMINI_API_KEY` and uses a completely different evaluation pipeline (Google Generative AI + scikit-learn). This is dead code that references a potentially sensitive environment variable name (`GEMINI_API_KEY`). `archive/evaluation_service.py` is a replaced by `pipeline_service.py`.
- **Files:** `archive/main.py`, `archive/evaluation_service.py`
- **Impact:** Dead code adds cognitive load, creates confusion about which pipeline is active, and the reference to `GEMINI_API_KEY` is misleading. The archive should be deleted or clearly documented.
- **Fix approach:** Delete `archive/` directory. The current pipeline (`pipeline_service.py`) is the active implementation.

### Database Migrations Silently Fail
- **Issue:** `database/postgres.py:26-32` iterates over `migration_*.sql` files and silently `pass`es on any exception. This means a failed migration (e.g., duplicate column, type conflict) is invisible.
- **Files:** `database/postgres.py:26-32`
- **Impact:** Schema can be in an inconsistent state without anyone knowing. Later code that depends on migrated columns will fail with confusing errors.
- **Fix approach:** Log migration failures and either re-raise or track applied migrations in a `_migrations` table so only unapplied migrations run.

### SQL Injection Risk via f-String in RepositoryRepository.related_data
- **Issue:** `repositories/repository_repository.py:90` uses an f-string to construct a SQL query:
  ```python
  return {table: db.execute(f"SELECT * FROM {table} WHERE repository_id=%s ORDER BY created_at DESC", (repository_id,)).fetchall() for table in tables}
  ```
  While `repository_id` is parameterized, the `table` names come from a hardcoded tuple at line 87-88. Currently safe because the table names are developer-controlled, but the pattern is fragile and any future dynamic table name would introduce SQL injection.
- **Files:** `repositories/repository_repository.py:86-90`
- **Impact:** Low now, but the pattern is a ticking bomb. If `tables` ever becomes user-controllable, it's a critical SQL injection.
- **Fix approach:** Validate table names against a whitelist:
  ```python
  VALID_TABLES = {"code_quality", "documentation", ...}
  assert table in VALID_TABLES, f"Invalid table: {table}"
  ```

### `print()` Statements Used Instead of Logging in Production Code
- **Issue:** Several files use `print()` for operational output rather than structured logging, making log aggregation and level-based filtering impossible.
- **Files:**
  - `services/github_service.py:67` — `print("Cloning:", url, "→", ...)`
  - `services/ollama_client.py:303-314` — `print()` in `__main__` block (less critical)
  - `pdf_gen.py:317, 424, 440` — progress prints
- **Impact:** Cannot control verbosity, no timestamps, no structured output for log aggregation tools.
- **Fix approach:** Replace with `logging.getLogger(__name__).info(...)`.

## Security Considerations

### Hardcoded Secret Key
- **Risk:** Session forgery and CSRF token manipulation.
- **Files:** `app.py:20`
- **Current mitigation:** None. The key is a hardcoded development-only value.
- **Recommendations:** Load from environment variable `FLASK_SECRET_KEY`. Rotate on deploy.

### GitHub Token Exposure Risk
- **Risk:** `GITHUB_TOKEN` is read from `os.environ` (`.env` file) and used as a Bearer token in all GitHub API calls. If any exception handler ever leaks response bodies or logs the request headers, the token could be exposed.
- **Files:** `services/github_service.py:12`
- **Current mitigation:** The token is used only in `Authorization` headers, never logged. No explicit sanitization.
- **Recommendations:** Add explicit guard: never log `self.headers` (which contains the Bearer token). Consider using GitHub App installation tokens for fine-grained permissions.

### Bare Exception Handlers Leak Internal Details
- **Risk:** `controllers/evaluation_controller.py` and several other controllers return `jsonify(error=str(exc))` with 500 status. This leaks internal implementation details (file paths, DB error messages, stack trace frames) to API consumers.
- **Files:** `controllers/evaluation_controller.py:27,42,54`, `controllers/report_controller.py:15,23`
- **Current mitigation:** None.
- **Recommendations:** Return generic error messages to clients. Log full details server-side.

### Old Gemini API Key Reference in Dead Code
- **Risk:** `archive/main.py:16` references `GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")`. If `.env` contains this key, it's accessible via dead code path.
- **Files:** `archive/main.py:16`
- **Current mitigation:** The `archive/` directory is excluded from the main import path.
- **Recommendations:** Delete `archive/` directory entirely.

## Performance Bottlenecks

### Synchronous Per-Repository Processing in Pipeline
- **Problem:** `PipelineService.evaluate_session_repositories` (`pipeline_service.py:87-106`) processes repositories sequentially in a `for` loop. Each repository evaluation can take 30-300 seconds (LLM inference). With 50+ repositories, this means 25+ minutes of wall-clock time for a session.
- **Files:** `services/evaluation/pipeline_service.py:87-106`
- **Cause:** Sequential loop with no parallelism across repositories.
- **Improvement path:** Use `concurrent.futures.ThreadPoolExecutor` to evaluate multiple repositories in parallel, bounded by a configurable `max_parallel_repos` setting. Consider a background task queue (Celery, RQ, or APScheduler) for large sessions.

### 30-Minute Hardcoded Timeout for PDF Generation
- **Problem:** `services/report_service.py:23` sets `timeout=1800` (30 minutes) for the `pdf_gen.py` subprocess. If the process hangs, the HTTP request thread is blocked for 30 minutes.
- **Files:** `services/report_service.py:23`
- **Cause:** The PDF generation is a single-threaded subprocess with a generous hard timeout.
- **Improvement path:** Move PDF generation to a background task. Return a 202 Accepted with a job ID, and poll for completion. Alternatively, reduce timeout and retry.

### Full-Snapshot Ingestion for Every Evaluation
- **Problem:** `orchestrator.py:231-253` re-runs the full ingestion pipeline (clone + parse + metrics + delta detection) on every evaluation. For repositories that have already been cloned and ingested, this is wasted work.
- **Files:** `services/evaluation/orchestrator.py:231-253`
- **Cause:** Ingestion is not cached per-repository across evaluations. Every `force=False` call still re-ingests because the orchestrator checks step files, not the ingestion DB.
- **Improvement path:** Check `ingestion_repository` for an existing record before re-ingesting. Only re-ingest if `force=True` or if no record exists.

### Evidence Truncation Without User Awareness
- **Problem:** `rubric_evaluation_agent.py:87-94` truncates evidence at 8000 characters with a logger warning. The agent still evaluates with truncated data, potentially producing inaccurate scores.
- **Similarly:** `feedback_agent.py:109-110` truncates the scores summary at 8000 chars.
- **Files:** `services/evaluation/rubric_evaluation_agent.py:87-94`, `services/evaluation/feedback_agent.py:109-110`
- **Cause:** Context window limits on the SLM models.
- **Improvement path:** Log the truncation ratio (e.g., "truncated 60% of evidence") so operators can identify when evaluation quality may be degraded. Consider adaptive prompting that summarizes truncated sections before passing to the model.

## Fragile Areas

### Evidence Router Uses Fuzzy String Matching
- **Files:** `services/evaluation/evidence_router.py:56-87`
- **Why fragile:** The `_find_best_routing_key` function uses case-insensitive substring matching in both directions (category contains key, key contains category). This is fragile — a rubric category code like "Q1A_implementation_details" could match "implementation" when it should match "documentation".
- **Safe modification:** When adding new EVIDENCE_ROUTING_MAP entries, ensure category codes are unambiguous. Consider prefix-based matching or exact match with a defined naming convention for rubric category codes.
- **Test coverage:** `tests/test_evidence_router.py` exists (276 lines) covering this module.

### Ingestion Service Has Deep Nesting & Single Responsibility Violation
- **Files:** `services/ingestion_service.py`
- **Why fragile:** 261 lines with 9 sequential stages (clone, metadata, discovery, parse, metrics, delta, build, write, persist), all in one method (`ingest()`). Any stage failure cascades into the `error` string accumulation pattern. Adding a new stage requires modifying this single massive method.
- **Safe modification:** Extract each stage into its own private method. Use dependency injection configuration for stage ordering.
- **Test coverage:** No dedicated test file for the ingestion service or any of the ingestion sub-modules (`code_parser.py`, `file_discoverer.py`, `delta_detector.py`, `metrics_calculator.py`, `snapshot_builder.py`).

### GitHub Service Retry/Error Handling Is Inconsistent
- **Files:** `services/github_service.py`
- **Why fragile:** Every API method wraps the body in `try/except Exception: return default_value`. There is no retry logic, no rate-limit handling (GitHub API returns 403 with `X-RateLimit-Remaining: 0`), no pagination protection for repos with >100 pages, and no logging on failure. If the GitHub API is slow or rate-limited, the entire pipeline silently returns empty data.
- **Safe modification:** Add `tenacity` retry decorator with exponential backoff for rate limits (retry-After header). Log warnings on API failures.
- **Test coverage:** No dedicated test file for `GitHubService`.

### Schema Validation in RepoUnderstandingAgent Falls Back to Default Output on Failure
- **Files:** `services/evaluation/repo_understanding_agent.py:89-110`, `code_understanding_agent.py:76-100`, `collaboration_agent.py:72-94`
- **Why fragile:** When schema validation fails, agents return a hardcoded fallback dict (e.g., `{"languages": repo_stats..., "structural_summary": "Schema validation failed..."}`). This means downstream pipeline stages receive valid-format but semantically empty data. The pipeline continues with `pipeline_status = "partial"` but the fallback data is indistinguishable from real data to consumers.
- **Safe modification:** Raise a distinct exception type on schema failure so the orchestrator can differentiate "agent ran but got low-quality results" from "agent failed entirely."
- **Test coverage:** Covered by `tests/test_agents.py` (501 lines) with schema validation tests.

### Database Initialization Runs on Every SessionService Instantiation
- **Files:** `services/session_service.py:11-13`
- **Why fragile:** `initialize_database()` is called in `SessionService.__init__()`, which is called on every Flask request via the service container. This means schema re-execution and migration re-attempts happen on every request. While Postgres's `IF NOT EXISTS` guards prevent errors, the migration loop re-attempts all migrations every time.
- **Safe modification:** Move `initialize_database()` to application startup in `app.py` `create_app()`, not in the service constructor.
- **Test coverage:** No test for `initialize_database()` behavior.

## Scaling Limits

### Known Capacity Constraints

| Resource | Current | Limit | Scaling Path |
|----------|---------|-------|-------------|
| Sequential repo evaluation | 1 repo at a time | Memory/thread pool | Parallel evaluation via ThreadPoolExecutor |
| LLM inference (Ollama client) | 300s timeout per call | Model context window | Use streaming, reduce max tokens |
| PDF generation timeout | 1800s / 30 min | HTTP request timeout | Background task queue |
| Evidence truncation | 8000 chars per criterion | Model context window | Hierarchical summarization |
| File count in prompts | 30 files (repo), 10 files (code) | Token budget | Dynamic chunking based on token count |

### Single-Process Bottleneck
- **Problem:** The entire Flask application runs in a single process with ASGI (`asgiref.wsgi.WsgiToAsgi`) wrapping the WSGI app. Long-running evaluations block the entire server from handling other requests.
- **Files:** `app.py:30`
- **Scaling path:** Separate the evaluation pipeline into a background worker process. Use PostgreSQL as the job queue. Flask handles only CRUD and status polling.

## Dependencies at Risk

### Ollama Model Availability
- **Risk:** The entire evaluation pipeline depends on two SLM models (`qwen2.5-coder:3b` and `phi-4-mini:3.8b`) being available on a local Ollama instance. If Ollama is down, models are not pulled, or GPU memory is insufficient, the pipeline fails immediately at `validate_connectivity()`.
- **Impact:** Pipeline cannot run without these specific models.
- **Migration plan:** Abstract model deployment behind a strategy pattern — allow plugging in remote API endpoints (OpenAI-compatible, Anthropic, etc.) as alternatives to local Ollama.

### psycopg v3 Binary Dependency
- **Risk:** `psycopg[binary]==3.2.9` in `requirements.txt` bundles a pre-compiled binary. This works on most platforms but can fail on unusual architectures (ARM, RISC-V). The `binary` extra also obscures the actual dependency.
- **Impact:** Installation failure on non-x86 platforms.
- **Migration plan:** Pin `psycopg>=3.2,<4.0` without the `[binary]` extra and document that `psycopg[c]` may be needed for performance.

### scikit-learn Imported but Only in Archived Code
- **Risk:** `scikit-learn==1.8.0` is in `requirements.txt` but only used in the archived `main.py` (via `TfidfVectorizer` and `cosine_similarity`). The active pipeline does not use scikit-learn.
- **Impact:** Unnecessary dependency adds ~50MB to the deployment and increased attack surface.
- **Migration plan:** Remove scikit-learn from `requirements.txt` since it's unused by the active pipeline.

## Test Coverage Gaps

### Untested Areas (High Priority)

| Area | Files | Risk | Priority |
|------|-------|------|----------|
| **Controllers** (6 files) | `controllers/*.py` | HTTP API layer has zero tests — broken endpoints ship silently | High |
| **GitHubService** | `services/github_service.py` | External API interaction with no contract tests | High |
| **Ingestion pipeline** | `services/ingestion_service.py`, `services/ingestion/*.py` | Core data pipeline has no unit tests | High |
| **Database layer** | `database/postgres.py`, `database/__init__.py` | Schema initialization and connection management untested | High |
| **Repositories** (5 files) | `repositories/*.py` | SQL query correctness is untested | High |
| **Flask integration** | `app.py` | App factory, blueprint registration, ASGI wrapping untested | Medium |
| **Service layer** (5 files) | `services/*.py` (github, ingestion, report, rubric, session) | Business logic orchestration untested | Medium |
| **PDF generation** | `pdf_gen.py` (440 lines) | Report generation is untested, requires real DB data | Medium |
| **Migration scripts** | `scripts/migrate_to_postgres.py` | One-time data migration untested | Medium |

### What IS Tested
- **Agent pipeline** (`tests/test_agents.py`): All 5 agents with mock Ollama — **good coverage**
- **Score aggregation** (`tests/test_score_aggregator.py`): Deterministic math with various scenarios — **good coverage**
- **Evidence routing** (`tests/test_evidence_router.py`): Route key matching and snapshot filtering — **good coverage**
- **Orchestrator** (`tests/test_orchestrator.py`): Pipeline lifecycle, retry logic, parallel execution — **good coverage**
- **Pipeline service** (`tests/test_pipeline_service.py`): High-level evaluation flow — **good coverage**
- **Schemas** (`tests/test_schemas.py`): JSON Schema validation — **good coverage**

### Integration Testing Gap
- **Files:** `tests/test_integration.py`
- **What's not tested:** The full pipeline end-to-end with real Ollama + real GitHub + real PostgreSQL. The integration test exists (122 lines) but is gated behind `RUN_INTEGRATION_TESTS=1` and is not run in CI.
- **Risk:** The interaction between ingestion, Ollama inference, and DB persistence is never validated in automated CI.
- **Priority:** Medium — mitigatable by manual smoke testing.

## Missing Critical Features

### No Evaluation Cancellation Mechanism
- **Problem:** Once an evaluation starts (especially session-level), there is no way to cancel it. The Flask request hangs until the pipeline completes or times out.
- **Blocks:** Operational control during long-running evaluations.
- **Fix approach:** Store evaluation job state in DB with a `cancel_requested` flag. Pipeline checks this flag between repository evaluations.

### No Authentication / User System
- **Problem:** The Flask app has no authentication middleware. Any user who can reach the server can create sessions, run evaluations, and view all results. The hardcoded secret key makes session forging trivial.
- **Blocks:** Deployment to any multi-tenant or internet-facing environment.
- **Fix approach:** Add Flask-Login or a simple token-based auth. Protect write endpoints.

### No Audit Logging
- **Problem:** There is no record of who performed what action. Session creation, repository addition, evaluation runs, and rubric modifications are not logged to an audit trail.
- **Blocks:** Academic integrity auditing.
- **Fix approach:** Add a simple `audit_log` table and middleware that logs all state-changing API calls.

---

*Concerns audit: 2026-07-13*
