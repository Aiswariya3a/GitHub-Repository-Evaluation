# Testing Patterns

**Analysis Date:** 2026-07-06

## Test Framework

**Runner:** Not detected
- No test runner config found — no `pytest.ini`, `setup.cfg`, `tox.ini`, `pyproject.toml`, `jest.config.*`, or `vitest.config.*`
- No `conftest.py` files anywhere in the project
- No test files exist in any directory (no `*.test.*`, `*.spec.*`, `test_*.py`, or `*_test.py` files)

**Assertion Library:** Not applicable — no tests exist

**Run Commands:** Not configured

## Test File Organization

**Location:** Not applicable

**Naming:** Not applicable

## Test Structure

**No test files or test suites exist anywhere in the codebase.**

The project has 29 Python source files totaling approximately 1,950 lines of application code with zero automated tests.

## Mocking

**Framework:** Not detected

**Patterns:** Not applicable

**Designed for Testability (observed patterns):**
- `ServiceContainer.build()` accepts a `root: Path` parameter, allowing test injection
- `EvaluationService.__init__()` accepts an optional `runner=None` parameter defaulting to `subprocess.run`, enabling mock injection for testing the subprocess call
- `SessionService.__init__()` accepts optional `repository=None` and `default_rubric_version_id=None`
- `RubricService.__init__()` accepts optional `repository=None`
- Several service constructors follow a dependency injection pattern via optional constructor parameters, which is favorable for unit testing

```python
# services/evaluation_service.py — testable by design
def __init__(self, root: Path, repositories: RepositoryService, runner=None):
    self.root, self.repositories = root, repositories
    self.runner = runner or subprocess.run
```

## Fixtures and Factories

**Test Data:**
- `data/` directory exists but no dedicated test fixtures found
- `example.env` provides a template for environment configuration
- CSV files (`repos.csv`, `selected_repos.csv`, `repo_report.csv`, `evaluation_report.csv`, `plagiarism_report.csv`) exist in the project root but are production data, not test fixtures

**Location:** Not applicable

## Coverage

**Requirements:** None enforced
- No coverage tooling (`pytest-cov`, `coverage.py`, `nyc`, `istanbul`) present in `requirements.txt`
- No `.coveragerc` or `pyproject.toml` coverage configuration

## Test Types

**Unit Tests:** Not present — zero unit tests across all 29 Python source files

**Integration Tests:** Not present

**E2E Tests:** Not present

## Gap Analysis

The following areas are entirely untested and represent risk:

| Area | Files | Lines | Risk |
|------|-------|-------|------|
| Gemini AI evaluation prompt/parsing | `main.py` | 495 | **High** — complex JSON parsing, error-prone regex, AI response handling |
| PDF generation logic | `pdf_gen.py` | 440 | **High** — complex table layout, data merging, file I/O |
| Database repositories (SQL) | `repositories/*.py` | ~310 | **Medium** — SQL correctness, edge cases |
| Flask API controllers | `controllers/*.py` | ~205 | **Medium** — request/response handling, error status codes |
| Service business logic | `services/*.py` | ~230 | **Medium** — validation rules, state transitions |
| Domain models | `models/domain.py` | 38 | **Low** — simple frozen dataclasses |
| Database connection | `database/postgres.py` | 24 | **Medium** — connection failures, schema migration |
| Flask app factory | `app.py` | 32 | **Low** — blueprint registration |
| Migration script | `scripts/migrate_to_postgres.py` | 120 | **Low-Medium** — legacy data migration one-time script |

## Recommendations for Adding Tests

**Recommended Framework:** `pytest` with `pytest-mock`

**Recommended Test Structure:**
```
tests/
├── conftest.py              # Shared fixtures (test app, mock DB, mock services)
├── test_app.py              # Flask app factory tests
├── controllers/
│   ├── test_session.py
│   ├── test_evaluation.py
│   ├── test_repository.py
│   ├── test_report.py
│   └── test_rubric.py
├── services/
│   ├── test_session_service.py
│   ├── test_evaluation_service.py
│   ├── test_repository_service.py
│   ├── test_github_service.py
│   ├── test_rubric_service.py
│   └── test_analysis_service.py
├── repositories/
│   ├── test_session_repository.py
│   ├── test_evaluation_repository.py
│   ├── test_repository_repository.py
│   └── test_rubric_repository.py
└── fixtures/
    ├── sample_evaluation.json
    └── mock_repos.csv
```

**Key Test Targets (priority order):**
1. `main.py:evaluate_code()` — Mock Gemini API, test JSON parsing, score clamping, rubric adherence
2. `controllers/evaluation_controller.py` — Session validation logic, error status code mapping
3. `services/evaluation_service.py` — Subprocess invocation, pending repo filtering, lock behavior
4. `repositories/evaluation_repository.py:flatten_metadata()` — Recursive dict flattening correctness
5. `services/github_service.py` — URL cleaning, sanitization edge cases
6. `services/analysis_service.py:added_code()` — Text diff line filtering

---

*Testing analysis: 2026-07-06*
