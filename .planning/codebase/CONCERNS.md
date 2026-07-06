# Codebase Concerns

**Analysis Date:** 2026-07-06

## Tech Debt

### Hardcoded Flask Secret Key
- **Issue:** `app.secret_key` is a hardcoded string `"repo-eval-workflow"` — identical across all deployments.
- **Files:** `app.py:19`
- **Impact:** Session signing uses a predictable key. If an attacker obtains any session cookie, they can forge arbitrary Flask session data. No environment variable override mechanism exists.
- **Fix approach:** Read `SECRET_KEY` from environment (e.g., `os.getenv("SECRET_KEY", os.urandom(32).hex())`) and generate a random fallback at startup.

### Debug Mode Enabled in Default Run
- **Issue:** `app.run(debug=True, host="0.0.0.0", port=5000)` enables the Werkzeug debugger and full tracebacks on port 5000 bound to all interfaces.
- **Files:** `app.py:32`
- **Impact:** In production-like environments, arbitrary remote code execution is possible through the debugger console. Stack traces may leak paths, environment variables, or query contents.
- **Fix approach:** Gate `debug=True` behind an environment variable check (e.g., `FLASK_ENV=development` or a `--debug` CLI flag).

### Hardcoded Plagiarism Threshold
- **Issue:** Cosine similarity threshold of 0.8 is hardcoded with no configuration override.
- **Files:** `main.py:485`
- **Impact:** Cannot tune sensitivity per session or rubric. A 0.79 result is silently discarded with no record. No mechanism exists to review near-miss pairs.
- **Fix approach:** Make the threshold a session-level setting or environment variable, and optionally log near-miss pairs.

### Hardcoded Base Repository URL
- **Issue:** The base/template repository URL is hardcoded at module level in `main.py`.
- **Files:** `main.py:25`
- **Impact:** Changing the base repo requires code modification. This URL is also session-specific (different assignments use different base repos) but is shared globally.
- **Fix approach:** Store the base repo URL as a session-level database column, or pass it as a CLI argument.

### Arbitrary Fixed Rate-Limit Sleep
- **Issue:** `time.sleep(1.2)` between repository evaluations is an arbitrary fixed delay with no connection to actual API rate limits.
- **Files:** `main.py:465`
- **Impact:** Too slow for large batches (60+ repos), too fast if GitHub API rate limits are hit. No retry or backoff logic exists.
- **Fix approach:** Check GitHub API `X-RateLimit-Remaining` headers and implement adaptive delay/retry.

### Arbitrary Code Truncation at 15000 Characters
- **Issue:** Both `evaluate_code` and `evaluate_code_dynamic` truncate submitted code to 15000 characters with no warning.
- **Files:** `main.py:306`, `main.py:386`
- **Impact:** Student submissions exceeding 15000 chars are silently truncated. The evaluator scores incomplete code, producing unreliable results with no audit trail.
- **Fix approach:** Log truncation events, consider the code length as part of evaluation metadata, and ideally support multi-turn Gemini invocations for large codebases.

### Models Module is Dead Code
- **Issue:** `models/domain.py` defines frozen dataclasses (`EvaluationSession`, `Repository`, `Evaluation`) that are never imported or used anywhere in the application. All data flows through raw dictionaries.
- **Files:** `models/domain.py` (all 3 classes), `models/__init__.py`
- **Impact:** 38 lines of dead code that create confusion about the type system. New contributors may think typed objects are in use when they are not.
- **Fix approach:** Either adopt the dataclasses throughout services/repositories (type-safe refactor), or remove the file entirely.

## Known Bugs

### GitHub Commit Count Extraction Fragile
- **Symptoms:** `commit_count` parses pagination links from the GitHub API `Link` header by splitting on `page=` and `>`. If GitHub changes the Link header format, this returns 0 silently.
- **Files:** `github_service.py:36-42`
- **Trigger:** Any repository whose commit list spans more than one page (per_page=1 is used, so effectively every repo with >1 commit triggers pagination parsing).
- **Workaround:** None — the method returns 0 on any exception, hiding the failure.
- **Fix:** Use a proper pagination library or parse the `Link` header with a regex/parser rather than fragile string splitting.

### Base Code Delta Can Include Comment-Only Differences
- **Symptoms:** `AnalysisService.added_code` compares line-by-line stripped content. If a student adds comments to a base-code line, the line appears different and is treated as "added," but functionally the change may be trivial. Conversely, whitespace-only changes get stripped away.
- **Files:** `services/analysis_service.py:4-7`
- **Trigger:** Any student who reformats or comments base code without adding logic will be credited with that code as their own.
- **Fix:** Use AST-level diffing or token-based comparison rather than line-level stripped text matching.

### Evaluate Code Uses Fragile JSON Extraction
- **Symptoms:** Both `evaluate_code` and `evaluate_code_dynamic` extract JSON from the Gemini response via regex and manual bracket matching (`text.find("{")`, `text.rfind("}")`). If the model returns markdown-wrapped JSON with nested braces (e.g., inside remarks), extraction can produce truncated or malformed JSON.
- **Files:** `main.py:314-319`, `main.py:389`
- **Trigger:** Gemini model returning explanatory text before/after JSON, or remarks containing brace characters.
- **Fix:** Use a strict JSON extraction strategy — request only raw JSON from the model, validate with `json.loads()`, and retry with a correction prompt on failure.

### Session "Progress" Values Are Display-Level Fictions
- **Symptoms:** The `session_context` function in `common.py` assigns hardcoded progress bar percentages: 100 for Completed, 50 for Evaluating, 8 for everything else.
- **Files:** `controllers/common.py:33`
- **Trigger:** Any non-Completed/Evaluating status gets 8%, which misrepresents actual progress (e.g., a newly added Pending repository shows near 0% progress as 8%).
- **Fix:** Remove the progress field entirely or derive it from actual steps in the pipeline rather than status-based arbitrary numbers.

## Security Considerations

### No Input Validation on Repository URLs or Roll Numbers
- **Risk:** Repository URLs and roll numbers from user input are passed directly to `subprocess.run(["git", "clone", ..., url, path])` in `github_service.py:33`. A malicious URL with shell metacharacters could lead to command injection, though mitigated by subprocess not using a shell. Roll numbers stored in filenames (`sanitize_name`) use a regex filter (`[^a-zA-Z0-9._-]`), providing basic sanitization.
- **Files:** `services/github_service.py:14-16`, `services/github_service.py:29-34`
- **Current mitigation:** `subprocess.run` does not use `shell=True`. The sanitize_name filter strips non-alphanumeric characters.
- **Recommendations:** Validate repo URLs with a URL parser before passing to git; validate roll numbers match expected patterns (e.g., university format). Add allow-list validation at the controller layer.

### No Rate Limiting or Authentication on API Endpoints
- **Risk:** All `/api/*` endpoints are publicly accessible with no authentication, authorization, or rate limiting. The API allows creating/archiving/deleting sessions and rubrics.
- **Files:** All controllers under `controllers/`
- **Current mitigation:** None.
- **Recommendations:** Add Flask session-based authentication (at minimum), rate limiting via Flask-Limiter, and CORS restrictions if exposed beyond localhost.

### GitHub Token Exposed as Module-Level Global
- **Risk:** `GITHUB_TOKEN` and `GEMINI_API_KEY` are loaded from environment and stored as module-level variables. The `HEADERS` dictionary in `main.py:21` includes the token in plaintext in memory for the process lifetime.
- **Files:** `main.py:14-15`, `main.py:21`
- **Current mitigation:** None — token is in a Python global for the entire process.
- **Recommendations:** Scope token access to individual function calls rather than module globals. Consider using a secrets manager.

### No CSRF Protection
- **Risk:** Flask-WTF CSRF protection is not used. State-changing POST/PUT/DELETE endpoints lack CSRF tokens. An attacker who tricks an admin into visiting a crafted page could create sessions, add repositories, or delete rubrics.
- **Files:** All `controllers/*.py` — no CSRF middleware or token validation.
- **Current mitigation:** None.
- **Recommendations:** Enable Flask-WTF CSRF protection globally, especially for endpoints that modify state.

## Performance Bottlenecks

### Sequential Repository Evaluation
- **Problem:** `main.py` processes repositories one at a time in a single loop with `time.sleep(1.2)` between iterations. For 100 repositories, this takes at least 2 minutes plus Gemini API time (often 5-15s per call) — potentially 15+ minutes total.
- **Files:** `main.py:425-465`
- **Cause:** Single-threaded sequential design with fixed sleep.
- **Improvement path:** Use concurrent.futures with controlled concurrency (e.g., 3-5 parallel workers) to overlap Gemini API calls. Remove the fixed sleep; use actual rate-limit awareness.

### All Code Read Into Memory at Once
- **Problem:** `read_code` concatenates all source file contents into a single in-memory string. For large repositories, this can be hundreds of KB/MB, and is then duplicated for TF-IDF vectorization.
- **Files:** `main.py:95-108`
- **Cause:** Naive concatenation without streaming or size limits.
- **Improvement path:** Set a per-repository code size limit, or sample files rather than reading everything. Stream code through generators where possible.

### Evaluation DB Per-Question N+1 Queries
- **Problem:** Hydrating evaluation data in `evaluation_repository.py:23-27` executes one query to fetch questions, then N queries for criteria (one per question). For a rubric with 10 questions, this is 11 round-trips per evaluation.
- **Files:** `repositories/evaluation_repository.py:22-27`
- **Cause:** Cursor-based per-question criteria fetching.
- **Improvement path:** Use a single JOIN query to fetch all questions and their criteria in one round trip.

### Repository Detail Loads 10 Extra Tables Via N+1
- **Problem:** `repository_repository.related_data()` executes 10 separate `SELECT *` queries to fetch insights for a single repository (one per table: code_quality, documentation, collaboration, project_health, technologies, contributors, commits, pull_requests, issues, files).
- **Files:** `repositories/repository_repository.py:79-83`
- **Cause:** Direct per-table querying without JOINs or lazy loading.
- **Improvement path:** Use a single query with JOINs across tables, or lazy-load tabs on the frontend via separate API endpoints.

### Dashboard Metrics Query Multiple Tables
- **Problem:** `dashboard_metrics` executes 5+ separate aggregate queries for the dashboard page. Each query scans large portions of the database.
- **Files:** `repositories/repository_repository.py:51-77`
- **Cause:** Modular but unoptimized query design.
- **Improvement path:** Introduce a materialized dashboard summary table that refreshes periodically, or combine queries into fewer round-trips.

### Duplicate Virtual Environments
- **Problem:** Two virtual environment directories exist: `venv/` (ignored in `.gitignore`) and `.venv/` (not listed in `.gitignore`). This causes confusion about which environment is active and wastes disk space.
- **Files:** `venv/`, `.venv/`, `.gitignore:1` (only `venv/` listed)
- **Fix:** Remove one of `venv/` or `.venv/`. Add the chosen one to `.gitignore`.

## Fragile Areas

### Gemini API Response Parsing
- **Files:** `main.py:310-321`, `main.py:388-390`
- **Why fragile:** JSON extraction relies on string operations (`text.find("{")`, `text.rfind("}")`) and regex to strip markdown wrapping. If the Gemini model changes its response format, adds nested braces in remarks, or returns structured content, the parsing fails with a generic "JSON parsing failed" error. The error details are passed back but not stored in the evaluation record.
- **Safe modification:** Add a validation retry loop: if initial JSON parsing fails, re-prompt the model asking it to fix the JSON. Log raw model output alongside parsed data for debugging.
- **Test coverage:** No tests exist for this parsing logic.

### Module-Level API Key Dependency
- **Files:** `main.py:14-15,28-29`
- **Why fragile:** `GITHUB_TOKEN` and `GEMINI_API_KEY` are loaded at module import time. If these environment variables are not set, `main.py` crashes at `genai.configure()` with a hard-to-debug error. Running `main.py` directly also re-executes the entire evaluation pipeline — there is no dry-run or validation-only mode.
- **Safe modification:** Wrap API configuration in a lazy-initialization function with clear error messages. Add a `--validate` flag that checks environment and connectivity without starting evaluation.

### Session Context Summary Relies on Map Lookups
- **Files:** `controllers/common.py:20-38`
- **Why fragile:** `session_context` iterates all repositories to build a summary, using dictionary access patterns like `repo_data.get("public") is True` and `repo_data.get("readme_exists") is True`. If a repository row lacks these fields (e.g., newly added, not yet checked), the boolean checks produce incorrect results. The commit_count defaults to 0 silently.
- **Safe modification:** Add explicit null/None checks and provide meaningful defaults. Log missing expected fields during hydration.

### PDF Generation Re-queries Database on Every Report
- **Files:** `pdf_gen.py:63-64`, `pdf_gen.py:101-106`
- **Why fragile:** PDF generation re-fetches all session repositories from the database, re-constructs DataFrames, resolves rubric snapshots, and generates individual PDFs for every student. If a session has 200+ repositories, this takes significant time and memory. A single failed PDF halts report generation.
- **Safe modification:** Generate PDFs individually on demand (already partially supported via `/sessions/.../repositories/.../report`). Skip or tolerate individual failures rather than failing the entire batch.

### evaluate_code_dynamic Single-Line Density
- **Files:** `main.py:365-408`
- **Why fragile:** This function uses extremely dense single-line expressions (e.g., `schema = {category["code"]: {**{...}, "total": 0} ...}` at lines 368-371, and inline semicolon-separated statements at line 389). The score-clamping logic at lines 392-405 is deeply nested in dictionary comprehensions. Any modification is error-prone.
- **Safe modification:** Break the function into clearly named helper functions for schema construction, prompt building, response parsing, and score clamping. Each helper should have a single responsibility.

### Subprocess Spawn for Evaluation and Reports
- **Files:** `services/evaluation_service.py:39-43`, `services/report_service.py:21-24`
- **Why fragile:** Both `EvaluationService` and `ReportService` spawn `main.py` or `pdf_gen.py` as subprocesses via `sys.executable`. This creates a new Python interpreter process for every operation. The subprocess inherits environment variables, the virtual environment must match, and the 1800-second timeout can kill long-running reports. Error messages from stderr are returned to the user via flash messages (in report generation) or raised as RuntimeError (in evaluation).
- **Safe modification:** Refactor `main.py` and `pdf_gen.py` into importable functions that can be called in-process. Remove the subprocess indirection entirely.

## Scaling Limits

### Single-Process Subprocess Architecture
- **Current capacity:** One evaluation at a time per server process. Each evaluation batches all pending repositories for a session and runs them sequentially.
- **Limit:** Multiple concurrent evaluation requests from different sessions execute serially due to `_evaluation_lock` in `evaluation_service.py:29`. The subprocess architecture also prevents horizontal scaling — only one Flask process can run evaluations.
- **Scaling path:** Replace subprocess-based evaluation with an async task queue (Celery/Redis or similar). Remove the global evaluation lock. Allow concurrent evaluations across sessions.

### Flattened Metadata Storage
- **Current capacity:** `flatten_metadata` recursively converts nested dicts/lists into key-value pairs with dot-notation keys (e.g., `questions.Q1A.score`).
- **Limit:** Deeply nested evaluation metadata (10+ levels) produces very long keys. Large lists produce many rows (one per list element), which increases DB storage linearly with no query benefit.
- **Scaling path:** Store complex metadata as a JSONB column rather than an EAV (entity-attribute-value) pattern. Query JSONB directly for the few cases where metadata is accessed.

## Dependencies at Risk

### Google Generative AI SDK (google-generativeai)
- **Risk:** The SDK (`google.generativeai`) is pinned in `requirements.txt` but may require frequent version updates to match Gemini model API changes. Version `0.8.x` added breaking changes to `GenerativeModel.generate_content()`. The evaluation pipeline depends entirely on correct JSON output from the model — any change to the response format breaks evaluation.
- **Impact:** Broken evaluations, silent score inaccuracies. No warning when the model returns unexpected output.
- **Migration plan:** Pin to a known-good version and test explicitly before upgrading. Add a model response validator that checks for expected JSON structure before proceeding.

### psycopg (v3)
- **Risk:** `psycopg` v3 is a relatively new major version with a smaller community than `psycopg2`. Compatibility issues with older PostgreSQL versions or unusual configurations may arise.
- **Impact:** Connection failures in deployment environments with custom PostgreSQL setups.
- **Migration plan:** Ensure minimum PostgreSQL version is documented. Fall back to `psycopg2-binary` if compatibility issues surface.

## Missing Critical Features

### No Evaluation Preview or Audit Trail
- **Problem:** Before running evaluations, there is no way to preview which code will be sent to the Gemini API, or verify that repository URLs are reachable. After evaluation, there is no audit trail showing what code was actually evaluated — only scores are stored.
- **Blocks:** Debugging incorrect evaluations, verifying evaluation fairness, reviewing edge cases.
- **Files:** `controllers/evaluation_controller.py`, `main.py`
- **Priority:** Medium

### No Cancellation for Running Evaluations
- **Problem:** Once evaluation is started, there is no way to cancel it. The subprocess runs until completion or the 1800-second timeout. Users cannot abort a misconfigured evaluation without restarting the server.
- **Blocks:** Operator control over the evaluation pipeline.
- **Files:** `services/evaluation_service.py`
- **Priority:** Low

### No Logging Framework for the Evaluation Pipeline
- **Problem:** `main.py` uses `print()` statements for all logging. There is no structured logging, log levels, or log file output. Debugging failed evaluations requires reading terminal output that may have scrolled away.
- **Blocks:** Post-mortem debugging of failed evaluations, production observability.
- **Files:** `main.py` (all `print()` statements), `services/evaluation_service.py` (uses `print()` at lines 35-38, 46)
- **Priority:** Medium

## Test Coverage Gaps

### No Test Files Exist
- **What's not tested:** The entire codebase. There are zero test files — no unit tests, integration tests, or end-to-end tests. All services, repositories, controllers, and the evaluation pipeline are untested.
- **Files:** All `.py` files under `services/`, `repositories/`, `controllers/`, `main.py`, `pdf_gen.py`, `database/postgres.py`
- **Risk:** Any code change may silently break evaluation logic, score clamping, database writes, PDF generation, or the Gemini integration. Refactoring is high-risk without a test safety net.
- **Priority:** High

### Critical Untested Logic
- **What's not tested:** Score clamping logic (`evaluate_code` lines 326-356), JSON parsing resilience, plagiarism threshold logic, session creation workflows, error recovery for failed repositories.
- **Files:** `main.py:326-356`, `main.py:310-321`, `repositories/evaluation_repository.py:48-70`
- **Risk:** The most complex and business-critical code (score clamping, JSON parsing, transaction evaluation save) has zero test coverage. A bug in score clamping would silently produce incorrect grades.
- **Priority:** High

---

*Concerns audit: 2026-07-06*
