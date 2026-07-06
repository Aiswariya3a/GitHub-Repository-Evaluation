# Coding Conventions

**Analysis Date:** 2026-07-06

## Naming Patterns

**Files:**
- `snake_case.py` — All Python files use lowercase with underscores (`app.py`, `session_service.py`, `repository_repository.py`)
- `UPPERCASE.md` — Documentation markdown files (`ARCHITECTURE.md`, `README.md`, `RUBRIC_MAPPING.md`)

**Functions:**
- `snake_case` for all functions and methods (`create_session()`, `list_repositories()`, `evaluate_pending()`)
- Private/helper methods prefixed with underscore (`_hydrate()`, `_insert_categories()`)
- Single-line functions often defined on same line as def (`def services(): return current_app.extensions["services"]`)
- Static methods use `@staticmethod` decorator on its own line

**Variables:**
- `snake_case` for all local variables (`session_id`, `repo_url`, `code_corpus`, `rubric_config`)
- Module-level constants in `UPPER_SNAKE_CASE` (`GITHUB_TOKEN`, `GEMINI_API_KEY`, `BASE_REPO`, `CLONE_DIR`, `DEFAULT_RUBRIC_ID`, `VALID_STATUSES`)

**Types:**
- `PascalCase` for classes (`SessionService`, `ServiceContainer`, `EvaluationRepository`, `RubricController`)
- Type hints inconsistently applied — some files use them (`__init__(self, root: Path, repositories: RepositoryService)` in `evaluation_service.py`), but many older files skip them entirely (`main.py` has no type annotations)
- Domain models use `@dataclass` with typed fields (`EvaluationSession`, `Repository`, `Evaluation` in `models/domain.py`)
- `Union` style uses `X | None` syntax (Python 3.10+) in `models/domain.py` (`total_out_of_80: Decimal | None`)

## Code Style

**Formatting:**
- No formatter detected — no `.prettierrc`, `.ruff.toml`, or `pyproject.toml` with formatting config
- Inconsistent spacing: some files (controllers, services) are dense with minimal whitespace; `main.py` and `pdf_gen.py` use generous blank lines
- No enforced line length limit — lines extend to 200+ characters in several files (`rubric_controller.py` line 29, `repository_repository.py` lines 67-69)
- Multiple statements on one line used occasionally: `row=db.execute("SELECT is_read_only FROM rubrics WHERE id=%s",(rubric_id,)).fetchone()` in `rubric_repository.py`
- Semicolons used in `main.py` line 389 to chain statements: `text = re.sub(r"^```json\s*", "", text); text = re.sub(r"\s*```$", "", text).strip()`
- Semicolons heavily used in inline JavaScript in templates for HTML attribute minimization

**Linting:**
- No linter config detected — no `.pylintrc`, `.flake8`, `pyproject.toml`, `ruff.toml`, `eslint`, or `biome.json`
- Code quality reliance is on manual review only

**String Style:**
- Double quotes `"..."` used consistently across all Python files
- Inline SQL in double-quoted strings with `%s` placeholders for psycopg parameters

**Indentation:**
- 4 spaces per level (PEP 8 standard)
- Single-space indentation sometimes used in densely packed multi-line expressions within `pdf_gen.py` style assignments
- Jinja2 template indentation uses 2 spaces

## Import Organization

**Order:**
1. **Standard library** — `import re`, `import os`, `from pathlib import Path`, `import json`
2. **Third-party** — `from flask import ...`, `import psycopg`, `import google.generativeai as genai`, `from sklearn...`
3. **Local application** — `from database import connect`, `from .common import services`
4. `from __future__ import annotations` used at the very top of `evaluation_service.py`, `report_service.py`, `database/postgres.py`, `scripts/migrate_to_postgres.py`

**Path Aliases:**
- No path aliases configured (no `pyproject.toml` or `sys.path` manipulation except in migration script)
- Intra-package imports use relative syntax: `from .common import services`, `from .repository_service import RepositoryService`
- `scripts/migrate_to_postgres.py` does `sys.path.insert(0, str(ROOT))` for access to app modules

**`__init__.py` Barrel Files:**
- Every package (`controllers/`, `services/`, `repositories/`, `database/`, `models/`) exports its public API via `__init__.py` using `from .module import ClassName` with `__all__`

## Error Handling

**Patterns:**
- **Service layer:** Raises typed exceptions — `ValueError` for input validation, `LookupError` for missing resources, `PermissionError` for forbidden operations (`session_service.py`, `rubric_service.py`)
- **Controller layer:** Catches exceptions from services and returns JSON error responses with appropriate HTTP status codes (`evaluation_controller.py`, `session_controller.py`)
- **Repository layer:** Exceptions propagate up; no try/except around database operations
- **Bare except:** Used in `main.py` lines 105-106 and 122-123 (`except: pass`) — an anti-pattern that silently swallows all exceptions
- **Gemini API calls:** Wrapped in try/except with fallback to error dict (`main.py` lines 309-361)

**Validation Pattern:**
```python
# session_service.py
def create_session(self, name, description="", rubric_version_id=None):
    name = str(name).strip()
    if not name:
        raise ValueError("Session name is required.")
```

**Error response pattern:**
```python
# Common pattern in controllers
return jsonify(error="Session not found."), 404
return jsonify(error=str(exc)), 400
```

## Logging

**Framework:** `print()` statements throughout — no logging module used.
- `main.py` uses `print()` for progress: `print(f"[{i+1}] Processing:", repo)`
- `evaluation_service.py` uses `print()` with `flush=True`
- `pdf_gen.py` uses `print()` for status: `print("Individual PDFs generated.")`
- Flash messages via Flask's `flash()` for UI feedback in `report_controller.py`

**Patterns:**
- `print("Cloning repo...")` simple status strings
- `print(f"[session {session_id}] Starting main.py for {len(pending)} repository/repositories...", flush=True)` formatted subprocess info
- No structured logging, no log levels, no log files

## Comments

**When to Comment:**
- Section headers using `# ---- TITLE ----` pattern in `main.py` and `pdf_gen.py`
- Occasional inline comments explaining logic decisions (`# CRITICAL: Clamp all scores to rubric maximums`)
- Docstrings on public module-level functions (`"""Evaluate student code against the rubric-based criteria."""`)
- Architecture notes at module top in `app.py` (`# All HTTP routes are registered through controller blueprints`)

**JSDoc/TSDoc:** Not applicable — this is a Python project

**Pattern:**
```python
# -----------------------------
# GEMINI EVALUATION
# -----------------------------

def evaluate_code(code, roll):
    """
    Evaluate student code against the rubric-based criteria.
    
    Rubric Structure (Total 80 marks):
    Q1A: 8 marks - Compilation and Execution
    ...
    """
```

## Function Design

**Size:**
- Most functions are small (1-15 lines) single-responsibility units
- `main.py:evaluate_code()` is the largest at ~200 lines, containing inline prompt template and JSON processing logic
- `pdf_gen.py:generate_preamble()` at ~100 lines is another notable large function

**Parameters:**
- Service methods typically accept 2-5 parameters
- Repository methods use `session_id`, `repository_id`, `rubric_version_id` UUIDs consistently
- Some functions accept optional overrides (`repository=None`, `runner=None`) for testability

**Return Values:**
- Services return dicts (from database rows) or raise exceptions
- Repositories return raw `dict_row` results from psycopg
- Boolean returns for status checks: `return bool(db.execute(...).rowcount)`
- Some methods chain returns with inline expressions: `def get(self, session_id): return self.repository.get(session_id)`

## Module Design

**Exports:**
- Each package `__init__.py` exports all public classes via explicit imports and `__all__` list

**Barrel Files:**
- `controllers/__init__.py` exports both classes and blueprint instances
- `services/__init__.py` exports all service classes
- `repositories/__init__.py` exports all repository classes

**Blueprint Registration Pattern:**
```python
# controllers/session_controller.py
session_controller = Blueprint("session", __name__)

# ... route handlers ...

class SessionController:
    blueprint = session_controller
```

**Layered Architecture:**
```
Controller (HTTP/Flask) → Service (business logic) → Repository (database) → PostgreSQL
```
- Controllers never access database directly
- Services orchestrate business logic and cross-repository operations
- Repositories handle raw SQL via psycopg

## Database Patterns

**Connection:**
- `with connect() as db:` context manager in every database method
- `connect()` returns `psycopg.connect()` with `dict_row` row factory
- SQL strings inline with `execute()`, `fetchone()`, `fetchall()`

**Schema Management:**
- `initialize_database()` reads `schema.sql` and executes it idempotently with `CREATE TABLE IF NOT EXISTS`
- Schema evolves via `ALTER TABLE ADD COLUMN IF NOT EXISTS` statements

---

*Convention analysis: 2026-07-06*
