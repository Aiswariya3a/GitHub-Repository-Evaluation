# Testing Patterns

**Analysis Date:** 2026-07-13

## Test Framework

**Runner:**
- **pytest** >=8.0, <9.0
- Config: `pytest.ini`

**Assertion Library:**
- Python built-in `assert` statements (standard pytest style)
- `jsonschema.validate()` for schema contract testing (raises `jsonschema.ValidationError` on failure)
- `pytest.raises()` for expected exception testing
- `pytest.approx()` for floating-point assertions in `test_score_aggregator.py`

**Run Commands:**
```bash
pytest                              # Run all tests (default: tests/ directory)
pytest -m "not integration"         # Run only unit tests (skip integration tests)
pytest -m integration               # Run only integration tests (requires RUN_INTEGRATION_TESTS=1)
pytest -v                           # Verbose mode
pytest --coverage                   # Coverage (if plugin installed — not in requirements.txt but available)
```

## Test File Organization

**Location:**
- All tests live under `tests/` directory — not co-located with source files
- Test files mirror source module naming: `test_<module>.py`

**Naming:**
- Test files: `test_<module_name>.py` (e.g., `test_agents.py`, `test_orchestrator.py`, `test_pipeline_service.py`)
- Test classes: `Test<ComponentName>` (e.g., `TestPipelineService`, `TestEvaluationOrchestrator`, `TestRouteEvidence`)
- Test methods: `test_<scenario>` (e.g., `test_instantiation_default`, `test_evaluate_repository`, `test_aggregate_basic`)

**Structure:**
```
tests/
├── __init__.py              # Empty package marker
├── conftest.py              # Shared fixtures (mock_ollama_client, sample_snapshot, sample_rubric, etc.)
├── test_agents.py           # Unit tests for all 5 evaluation agents (501 lines)
├── test_evidence_router.py  # Evidence routing logic tests (276 lines)
├── test_integration.py      # Full pipeline integration test (122 lines)
├── test_orchestrator.py     # Orchestrator tests (460 lines)
├── test_pipeline_service.py # PipelineService tests (160 lines)
├── test_schemas.py          # JSON Schema contract tests (399 lines)
└── test_score_aggregator.py # Score aggregation tests (403 lines)
```

**Total: 8 test files, ~102 unit tests across 7 files (1 integration test file).**

## Test Structure

**Suite Organization:**
```python
# tests/test_agents.py
class TestRepoUnderstandingAgent:
    """Tests for RepoUnderstandingAgent — repository structure analysis."""

    def test_repo_understanding_agent_run(self, mock_ollama_client, sample_snapshot):
        """Agent returns valid repo understanding output matching schema."""
        # Arrange
        mock_ollama_client.infer.return_value = {...}
        agent = RepoUnderstandingAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(sample_snapshot)

        # Assert
        jsonschema.validate(instance=result, schema=REPO_UNDERSTANDING_SCHEMA)
        assert "languages" in result
        assert result["languages"]["C"] == 3
```

**Key Patterns:**
- **Arrange/Act/Assert** — comments clearly demarcate each section
- **Docstrings on every test method** describe what scenario is being validated
- **Class-based grouping** per component under test
- **Section separators** with `# --- Section Name ---` for long test files

**Edge case patterns covered:**
- Empty/None inputs (empty snapshots, missing metadata)
- Schema validation failures (invalid LLM output triggers fallback)
- Score clamping (scores exceeding max_score, negative scores)
- Low confidence detection (confidence < 0.5 → `confidence_warning=True`)
- Error isolation (one agent failing doesn't crash the pipeline)
- Corrupted file handling (invalid JSON in step output)

## Mocking

**Framework:** `unittest.mock` (standard library) — `MagicMock`, `patch`, `PropertyMock`
Also: `pytest-mock` via `mocker` fixture (used in `tests/conftest.py` for `mock_rubric_service`)

**Patterns:**
```python
# Standard MagicMock pattern (preferred in most test files)
from unittest.mock import MagicMock, patch

def test_evaluate_repository(self):
    mock_orch = MagicMock()
    mock_orch.evaluate.return_value = {"pipeline_status": "success", "total_score": 7.5}
    svc = PipelineService(orchestrator=mock_orch)
    result = svc.evaluate_repository(...)
    mock_orch.evaluate.assert_called_once_with(...)

# Replace entire module with MockRepoService
with patch("services.repository_service.RepositoryService") as MockRepoService:
    mock_repo_svc = MagicMock()
    mock_repo_svc.pending_repositories.return_value = [...]
    MockRepoService.return_value = mock_repo_svc

# Mock with side_effect for sequential returns
mock_orch.evaluate.side_effect = [
    {"pipeline_status": "success", "total_score": 7.0},
    {"pipeline_status": "partial", "total_score": 5.0},
]

# Mock exception simulation
mock_orch.evaluate.side_effect = [
    {"pipeline_status": "success"},
    Exception("Repository error"),
    {"pipeline_status": "success"},
]
```

**Shared fixtures in `conftest.py`:**
```python
@pytest.fixture
def mock_ollama_client():
    client = MagicMock()
    client.infer.return_value = {"response": json.dumps({"result": "ok"})}
    client.validate_connectivity.return_value = {
        "connected": True,
        "available_models": ["qwen2.5-coder:3b", "phi-4-mini:3.8b"],
        "missing_models": [],
    }
    return client

@pytest.fixture
def mock_rubric_service(mocker):
    svc = mocker.MagicMock()
    svc.default_version_id = "test-rubric-version-id"
    svc.get_version.return_value = {...}
    return svc
```

**What to Mock:**
- **OllamaClient** — all agent tests mock the `infer()` method to return controlled responses
- **EvaluationOrchestrator** — `PipelineService` tests mock the orchestrator
- **RepositoryService** — pipeline session tests mock repository services
- **External services** — never called in unit tests (Ollama, PostgreSQL, GitHub)

**What NOT to Mock:**
- **Pure functions** — `aggregate_scores()` in `score_aggregator.py`, `route_evidence()` in `evidence_router.py` are tested with real data
- **JSON Schemas** — schema contract tests use real schemas with real `jsonschema.validate()`
- **Dataclasses** — `AggregatedScore`, `CriterionEvaluation`, etc. are instantiated directly

## Fixtures and Factories

**Test Data (`conftest.py`):**
```python
@pytest.fixture
def sample_snapshot():
    """Sample ProjectSnapshot dict for testing capability agents."""
    return {
        "repository_metadata": {...},
        "github_metadata": {...},
        "repo_stats": {...},
        "files": [...],
        "delta": None,
        "ingestion_metadata": {...},
    }

@pytest.fixture
def sample_rubric():
    """Sample rubric config for testing evaluation and aggregation."""
    return {"id": "test-rubric-uuid", "categories": [...], ...}

@pytest.fixture
def sample_criterion_result():
    """Sample individual criterion evaluation result dict."""
    return {"criterion_key": "compilation", "score": 3.5, ...}
```

**Inline test factories (defined per test file):**
```python
# test_evidence_router.py
def _make_snapshot(overrides=None) -> dict:
    snapshot = {"repository_metadata": {...}, "repo_stats": {...}, ...}
    if overrides: snapshot.update(overrides)
    return snapshot

# test_score_aggregator.py
def _make_rubric(categories: list[dict]) -> dict:
    return {"id": "test-rubric", "categories": categories, ...}

def _make_criterion_result(criterion_key, category_code, score, max_score=4.0, ...) -> dict:
    return {"criterion_key": criterion_key, "category_code": category_code, ...}

# test_orchestrator.py
def _make_minimal_snapshot(self):
    return {"repo_stats": {...}, "files": [], ...}
```

**Shared vs. file-specific:**
- Shared fixtures → `conftest.py` (used across test files)
- File-specific factories → defined at module level in each test file (prefixed with `_`)

## Coverage

**Requirements:** Not enforced — no coverage tool or minimum threshold configured in `pytest.ini` or `requirements.txt`.

**View Coverage:**
```bash
pytest --cov=services --cov=controllers --cov=models --cov=repositories  # If pytest-cov installed
```

**Current coverage gaps (observed):**
- `controllers/` — no controller tests exist (all controllers are untested)
- `services/github_service.py` — no tests for GitHub API interactions
- `services/ingestion/` — no unit tests for `FileDiscoverer`, `CodeParser`, `MetricsCalculator`, `DeltaDetector`, `SnapshotBuilder`
- `services/report_service.py`, `services/analysis_service.py`, `services/session_service.py`, `services/rubric_service.py` — no service-level tests
- `repositories/` — no repository-layer tests
- `services/ollama_client.py` — no tests for the `OllamaClient` itself
- `services/container.py` — no tests for `ServiceContainer.build()`
- `pdf_gen.py`, `scripts/` — untested

## Test Types

**Unit Tests (7 files, ~102 tests):**
- All agent tests (`test_agents.py`) — 14 tests across 5 agent classes
- Orchestrator tests (`test_orchestrator.py`) — 15 tests (instantiation, workflow, error handling, recovery)
- PipelineService tests (`test_pipeline_service.py`) — 8 tests
- Evidence router tests (`test_evidence_router.py`) — 28 tests across 4 test classes
- JSON Schema contract tests (`test_schemas.py`) — 20+ tests across 5 schema test classes
- Score aggregation tests (`test_score_aggregator.py`) — 14 tests across 5 test classes
- All use mocked OllamaClient, mocked DB — no external services required

**Integration Tests (1 file, 2 tests):**
- `test_integration.py` — `TestFullPipeline` class with `test_full_pipeline_evaluation` and `test_pipeline_with_specific_rubric`
- Marked `@pytest.mark.integration`
- Opt-in via `RUN_INTEGRATION_TESTS=1` environment variable
- Requires running Ollama instance with specific models, a public GitHub repo, and PostgreSQL

**E2E Tests:**
- Not used — no E2E framework detected

## Common Patterns

**Async Testing:**
- Not applicable — the codebase is synchronous Python (no asyncio). Threads via `ThreadPoolExecutor` are tested synchronously.

**Error Testing:**
```python
# Expected exception testing
with pytest.raises(jsonschema.ValidationError):
    jsonschema.validate(instance=invalid, schema=REPO_UNDERSTANDING_SCHEMA)

# Side effect exception (mock raises)
mock_agent.run.side_effect = Exception("Ollama unavailable")
```

**Schema Validation Testing:**
```python
# Valid data must pass
jsonschema.validate(instance=self.VALID_DATA, schema=REPO_UNDERSTANDING_SCHEMA)

# Schema meta-validation
jsonschema.Draft7Validator.check_schema(schema)

# Missing required field must fail
invalid = dict(self.VALID_DATA)
del invalid["languages"]
with pytest.raises(jsonschema.ValidationError):
    jsonschema.validate(instance=invalid, schema=REPO_UNDERSTANDING_SCHEMA)
```

**Recovery/File-state Testing (orchestrator):**
```python
# Uses tempfile.TemporaryDirectory for isolated filesystem tests
with tempfile.TemporaryDirectory() as tmp:
    orch = EvaluationOrchestrator(working_dir=tmp, ...)
    # Write fake step output
    step_path = orch._step_output_path(tmp, "aggregation")
    os.makedirs(os.path.dirname(step_path), exist_ok=True)
    with open(step_path, "w") as f:
        json.dump({"total_score": 5.0}, f)
    # Verify recovery detection
    completed = orch._detect_completed_steps(tmp)
    assert "aggregation" in completed
```

**pytest.ini configuration:**
```ini
[pytest]
markers =
    integration: marks tests that require Ollama and PostgreSQL (deselect with '-m "not integration"')
testpaths = tests
```

---

*Testing analysis: 2026-07-13*
