"""Abstract base class for all evaluation agents.

Defines the `run()` contract (per D-01) that all agents implement,
along with shared utilities for output validation and persistence.

All agents inherit from BaseAgent and implement `run()`.
Default execution is in-process (D-01). Subprocess mode available
via config flag (D-02).
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Optional

import jsonschema
from services.ollama_client import OllamaClient


class BaseAgent(ABC):
    """Abstract base class for all evaluation agents.

    Provides the standard `run()` interface (per D-01) that all
    capability extraction, rubric evaluation, and feedback agents
    implement. Includes shared utilities for JSON Schema validation
    and idempotent file-based output writing.

    Args:
        ollama_client: Pre-configured OllamaClient instance. If None,
            a new one is created (default config).
        execution_mode: Either "in_process" (default) or "subprocess".
            Subprocess mode is a passthrough flag — actual subprocess
            spawning is handled by the orchestrator (ORC-02).
    """

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        execution_mode: str = "in_process",
    ):
        self.ollama = ollama_client or OllamaClient()
        self.execution_mode = execution_mode

    @abstractmethod
    def run(
        self,
        input_data: dict,
        output_path: Optional[str] = None,
    ) -> dict:
        """Execute agent logic.

        Args:
            input_data: Input dictionary (e.g., ProjectSnapshot slice
                for capability agents, or individual criterion with
                evidence for rubric evaluation).
            output_path: If provided, agent writes validated output
                to this JSON file path (idempotent per D-11).

        Returns:
            dict: Agent output (capability extraction, evaluation,
                or feedback).
        """
        ...

    def _write_output(self, output: dict, output_path: str) -> None:
        """Write validated output JSON to file (idempotent per D-11).

        Creates parent directories as needed. Writes human-readable
        JSON with sorted keys for diff-friendly output.

        Args:
            output: Validated output dictionary.
            output_path: Target file path for the JSON output.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str, sort_keys=True)

    def _validate_output(
        self,
        output: dict,
        schema: dict,
    ) -> tuple[bool, list[str]]:
        """Validate output dictionary against a JSON Schema.

        Uses the jsonschema library to validate agent output against
        its expected schema contract.

        Args:
            output: Output dictionary to validate.
            schema: JSON Schema dict (draft-07).

        Returns:
            tuple[bool, list[str]]: (is_valid, list_of_error_messages)
        """
        try:
            jsonschema.validate(instance=output, schema=schema)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e)]
        except jsonschema.SchemaError as e:
            return False, [f"Schema error: {e}"]
