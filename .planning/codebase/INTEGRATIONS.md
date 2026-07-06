# External Integrations

**Analysis Date:** 2026-07-06

## APIs & External Services

**AI / LLM:**
- **Google Gemini** - AI-based code evaluation against a rubric
  - SDK: `google-generativeai==0.8.6`
  - Model: `gemini-2.5-flash` (configured in `main.py:29`)
  - Auth: `GEMINI_API_KEY` env var
  - Usage: Student code is sent via prompt to generate structured JSON evaluation scores for 10 rubric questions (Q1A-Q5B)
  - Prompt includes full rubric definition, max score constraints, and code (truncated to 15,000 chars)
  - Rate limiting: 1.2s sleep between evaluations (`time.sleep(1.2)` in `main.py:465`)

**Version Control / Source Code:**
- **GitHub REST API v3** - Repository validation and commit counting
  - SDK: `requests` library (direct HTTP calls)
  - Auth: `GITHUB_TOKEN` env var (passed as `Authorization: token <token>` header)
  - Endpoints used:
    - `GET /repos/{owner}/{repo}` — check repo existence and visibility (`services/github_service.py:23`)
    - `GET /repos/{owner}/{repo}/contents` — list root files for README detection (`services/github_service.py:25`)
    - `GET /repos/{owner}/{repo}/commits?per_page=1` — commit count via `Link` header pagination (`services/github_service.py:39`)

## Data Storage

**Databases:**
- **PostgreSQL** (primary and only database)
  - Connection: `DATABASE_URL` env var (e.g. `postgresql://postgres:postgres@localhost:5432/repository_evaluation`)
  - Client: `psycopg` 3.2.9 (binary distribution) with `dict_row` row factory
  - Module: `database/postgres.py`
  - Schema: `database/schema.sql` (16 tables, ~20 indexes)
  - Auto-initialized on app startup via `initialize_database()` (idempotent — uses `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ADD COLUMN IF NOT EXISTS`)

**Database Schema (16 tables):**
| Table | Purpose |
|-------|---------|
| `evaluation_sessions` | Root aggregate — evaluation session metadata |
| `repositories` | Repositories within a session, with evaluation status |
| `evaluations` | Top-level evaluation results per repository |
| `evaluation_questions` | Per-question breakdown (Q1A–Q5B etc) |
| `evaluation_criteria` | Per-criterion scores and remarks |
| `evaluation_metadata` | Arbitrary key-value metadata on evaluations |
| `rubrics` | Rubric definitions (System/Custom) |
| `rubric_versions` | Versioned rubric snapshots |
| `rubric_categories` | Category definitions within a rubric version |
| `rubric_criteria` | Criterion definitions within a category |
| `plagiarism_results` | Plagiarism similarity pairs per session |
| `code_quality`, `documentation`, `collaboration`, `project_health` | Repository metrics tables |
| `technologies`, `contributors`, `commits`, `pull_requests`, `issues`, `files` | Repository inspection data |

**File Storage:**
- **Local filesystem only**
  - Cloned repos stored in `repos/` directory (auto-created, gitignored)
  - Student PDF reports stored in `student_reports/` directory (gitignored)
  - Consolidated PDF written to project root as `Final_Consolidated_Report.pdf`

**Caching:**
- None detected

## Authentication & Identity

**Auth Provider:**
- None. The application uses a hardcoded `app.secret_key = "repo-eval-workflow"` for Flask session signing in `app.py:19`
- No user authentication, login, or identity management
- The app is designed for local/trusted-network use only

## Monitoring & Observability

**Error Tracking:**
- None. Errors are printed to stdout/stderr (Flask terminal output). No Sentry, Datadog, or similar.

**Logs:**
- Plain `print()` statements throughout the codebase (`main.py`, `services/`)
- Flask development server logging (stdout/stderr)
- No structured logging, no log levels, no log file persistence

## CI/CD & Deployment

**Hosting:**
- None. Runs locally with Flask development server only.

**CI Pipeline:**
- None. No `.github/workflows/`, no CI config files detected.

## Environment Configuration

**Required env vars:**
- `GITHUB_TOKEN` — GitHub personal access token (classic or fine-grained with repo access)
- `GEMINI_API_KEY` — Google AI Studio API key for Gemini
- `DATABASE_URL` — PostgreSQL connection URL (`postgresql://user:pass@host:port/dbname`)

**Secrets location:**
- `.env` file in project root (listed in `.gitignore`)
- Example template: `example.env`

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Other Integrations

**Google Fonts:**
- Inter and JetBrains Mono fonts loaded from `fonts.googleapis.com` in `templates/base.html:6-7`

**Subprocess Executables (system dependencies):**
- `git` — used for shallow cloning (`git clone --depth 1`) in `services/github_service.py:33`
- `python` — used to spawn `main.py` and `pdf_gen.py` as subprocesses from Flask (`services/evaluation_service.py:40`, `services/report_service.py:22`)
- These require `git` CLI to be installed on the host system

---

*Integration audit: 2026-07-06*
