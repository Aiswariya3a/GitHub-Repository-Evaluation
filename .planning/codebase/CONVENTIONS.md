# Coding Conventions

**Analysis Date:** 2026-07-13

## Naming Patterns

**Files:**
- Python modules use `snake_case.py` (e.g., `evaluation_controller.py`, `pipeline_service.py`, `ollama_client.py`)
- Test files use `test_<module_name>.py` (e.g., `test_agents.py`, `test_orchestrator.py`)
- Package `__init__.py` files present in all subpackages

**Functions:**
- `snake_case` for all functions and methods (e.g., `evaluate_repository()`, `_run_agent_with_retry()`, `route_evidence()`)
- Private/helper methods prefixed with underscore (e.g., `_step_output_path()`, `_detect_completed_steps()`, `_filter_snapshot()`)
- Static methods on agents use `@staticmethod` decorator (e.g., `_normalize_output()` in `repo_understanding_agent.py`)
- Abstract methods inherited from `BaseAgent` use `@abstractmethod`

**Variables:**
- `snake_case` for all variables (e.g., `session_dir`, `criterion_results`, `mock_ollama_client`)
- Constants in `UPPER_SNAKE_CASE` (e.g., `REPO_UNDERSTANDING_SCHEMA`, `FEEDBACK_SCHEMA`, `EVIDENCE_ROUTING_MAP`, `VALID_STATUSES`, `FEEDBACK_SYSTEM_PROMPT`)

**Types:**
- Classes use `PascalCase` (e.g., `EvaluationOrchestrator`, `PipelineService`, `RepoUnderstandingAgent`, `OllamaClient`, `AggregatedScore`)
- Custom exceptions use `PascalCase` with `Error` suffix (e.g., `OllamaConnectionError`, `OllamaModelNotFoundError`, `OllamaAPIError`)
- Dataclasses use `PascalCase` (e.g., `RepositoryMetadata`, `ProjectSnapshot`, `CriterionEvaluation`, `CategoryScore`)

## Code Style

**Formatting:**
- No explicit formatter config detected (no `.prettierrc`, `biome.json`, etc.) — standard Python style
- Indentation: 4 spaces (Python standard)
- Line length: varied, some long single-expression lines in controller routes
- Imports sorted: standard library first, then third-party, then local (separated by blank lines)

**Linting:**
- No linter config files detected (no `.eslintrc*`, `setup.cfg` with flake8, `pyproject.toml` with ruff/black, etc.)

## Import Organization

**Order (consistent across all files):**
1. Standard library modules (`json`, `os`, `logging`, `abc`, `typing`, `dataclasses`)
2. Third-party libraries (`pytest`, `flask`, `jsonschema`, `requests`, `pydantic`)
3. Local application imports (from `services`, `models`, `repositories`, `controllers`)

**Examples of patterns:**

From `services/evaluation/orchestrator.py`:
```python
import json
import os
import shutil
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

from services.evaluation.repo_understanding_agent import RepoUnderstandingAgent
from services.evaluation.schemas import (
    REPO_UNDERSTANDING_SCHEMA,
    CODE_UNDERSTANDING_SCHEMA,
    ...
)
```

From `tests/test_agents.py`:
```python
import json
from unittest.mock import MagicMock, PropertyMock

import jsonschema
import pytest

from services.evaluation.repo_understanding_agent import RepoUnderstandingAgent
from services.evaluation.schemas import (
    REPO_UNDERSTANDING_SCHEMA,
    ...
)
```

**Path Aliases:**
- All local imports use full package paths relative to project root (e.g., `from services.evaluation.agent_base import BaseAgent`, `from models.evaluation_models import AggregatedScore`)
- No import aliases (`as`) used except for standard library modules where needed

**Barrel files (`__init__.py`):**
- `services/__init__.py`: re-exports all service classes
- `services/evaluation/__init__.py`: re-exports agents, schemas, prompts, orchestrator, pipeline, utility functions
- `models/__init__.py`: re-exports `EvaluationSession` and `Repository` dataclasses
- `repositories/__init__.py`: re-exports all repository classes
- `tests/__init__.py`: empty file (package marker only)
- All barrel files define `__all__` lists

## Error Handling

**Patterns:**

1. **Custom exception classes** for domain-specific errors:
   ```python
   # services/ollama_client.py
   class OllamaConnectionError(Exception):
       def __init__(self, message: str = ""):
           super().__init__(message or "Cannot connect to Ollama. ...")

   class OllamaModelNotFoundError(Exception):
       def __init__(self, model: str, message: str = ""):
           self.model = model
           super().__init__(message or f"Required model '{model}' is not available. ...")
   ```

2. **Try/except with graceful fallback** — agents catch LLM failures and return safe fallback output:
   ```python
   # services/evaluation/repo_understanding_agent.py
   try:
       result = self.ollama.infer(...)
   except ...:
       result = {
           "languages": repo_stats.get("language_breakdown", {}),
           "key_files": [...],
           "structural_summary": "Schema validation failed — unable to generate analysis.",
           ...
       }
   ```

3. **Retry logic with logging** — orchestrator retries agent calls on failure:
   ```python
   # services/evaluation/orchestrator.py
   def _run_agent_with_retry(self, agent, agent_name, ...):
       for attempt in range(1 + self.max_retries):
           try:
               result = agent.run(input_data, output_path)
               valid, errors = agent._validate_output(result, schema)
               if valid:
                   return result
           except Exception as e:
               logger.error(f"{agent_name} attempt {attempt + 1}: error: {e}")
       self.failed_agents.append(agent_name)
       return None
   ```

4. **HTTP error responses** — controllers return `(jsonify(error=...), status_code)` tuples:
   ```python
   # controllers/evaluation_controller.py
   if not session:
       return None, (jsonify(error="Session not found."), 404)
   ```

5. **Exception chaining** with `raise ... from exc`:
   ```python
   # services/container.py
   except Exception as exc:
       raise RuntimeError(f"Failed to initialize PipelineService: {exc}") from exc
   ```

6. **Guard clauses** for missing data — functions check for None/empty and return early:
   ```python
   if not snapshot:
       return {"status": "failed", "error": "Ingestion produced no snapshot", ...}
   ```

## Logging

**Framework:** Python standard `logging` module.

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)` at top of every module
- Five distinct log levels used: `debug`, `info`, `warning`, `error`, `exception` (via logger.exception)
- Structured log messages with context (agent name, attempt count, file counts)
- No structured logging (JSON) — plain text messages

**Examples:**
```python
logger.info(f"Recovery: {step} output found at {path}, skipping")
logger.warning(f"Recovery: {step} output corrupted at {path}, will re-run")
logger.error(f"Failed to persist results to PostgreSQL: {e}")
logger.debug("Routing criterion '%s' -> key '%s' -> %d sections", category, key, len(sections))
```

## Comments

**When to Comment:**
- Module-level docstrings explain purpose of each file (in `"""triple quotes"""`)
- Class-level docstrings describe responsibilities and design decisions
- Method-level docstrings follow Google-style with `Args:`, `Returns:`, `Raises:` sections
- Inline comments for non-obvious logic or cross-references to design documents (e.g., `# ORC-03`, `# D-11`, `# EVA-07`, `# T-02-04`)
- Section separators: `# --- Step 1: Ingestion ---`
- Test docstrings explain what scenario is being tested (e.g., `"""Agent returns valid repo understanding output matching schema."""`)

**JSDoc/TSDoc:**
- Not applicable (Python project)

## Function Design

**Size:**
- Agent `run()` methods: ~50-80 lines
- Orchestrator methods: up to ~70 lines for `_run_agent_with_retry`, ~250 lines for `evaluate()` (the main pipeline method)
- Controller endpoints: typically 5-15 lines
- Helper/utility functions: 10-25 lines

**Parameters:**
- Type annotations always used (e.g., `def run(self, input_data: dict, output_path: Optional[str] = None) -> dict:`)
- Optional parameters default to `None` or sensible defaults
- Keyword arguments for configuration in constructors

**Return Values:**
- Always typed (functions that can fail return `Optional[dict]` with `None` for failure)
- Consistent dict-shaped returns with `pipeline_status`, `total_score`, etc.

## Module Design

**Exports:**
- Each `__init__.py` barrel file uses explicit `__all__` lists
- Individual modules export all public classes/functions (no `__all__` in non-barrel files)

**Barrel Files:**
- `services/__init__.py` exports all service classes
- `services/evaluation/__init__.py` exports agents, schemas, prompts, router, pipeline
- `models/__init__.py` exports domain dataclasses
- `repositories/__init__.py` exports all repository classes

## Class Design

**Flask Blueprint pattern** in controllers:
```python
# controllers/evaluation_controller.py
evaluation_controller = Blueprint("evaluation", __name__)

@evaluation_controller.post("/api/sessions/<session_id>/evaluate")
def evaluate_session(session_id):
    ...

class EvaluationController:
    blueprint = evaluation_controller
```

**Abstract Base Agent pattern:**
```python
class BaseAgent(ABC):
    def __init__(self, ollama_client=None, execution_mode="in_process"):
        self.ollama = ollama_client or OllamaClient()
        self.execution_mode = execution_mode

    @abstractmethod
    def run(self, input_data: dict, output_path=None) -> dict: ...
```

**Dataclass models** for type-safe data contracts:
```python
@dataclass
class AggregatedScore:
    total_score: float
    max_score: float
    normalized_to_20: float
    percentage: float
    categories: list[CategoryScore] = field(default_factory=list)
    low_confidence_criteria: list[str] = field(default_factory=list)
```

---

*Convention analysis: 2026-07-13*
