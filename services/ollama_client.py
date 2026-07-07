"""Ollama HTTP client for SLM inference with model routing and startup validation.

Provides connectivity validation, model availability checks, and temperature=0
inference with configurable host/port via environment variables.

Custom exceptions:
    - OllamaConnectionError: Connection failures
    - OllamaModelNotFoundError: Required model not pulled
    - OllamaAPIError: API response errors
"""

import json
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class OllamaConnectionError(Exception):
    """Raised when connection to Ollama server fails."""

    def __init__(self, message: str = ""):
        super().__init__(
            message
            or "Cannot connect to Ollama. Ensure Ollama is running "
            "(start with 'ollama serve' or launch the application)."
        )


class OllamaModelNotFoundError(Exception):
    """Raised when a required model is not available on the Ollama server."""

    def __init__(self, model: str, message: str = ""):
        self.model = model
        super().__init__(
            message
            or f"Required model '{model}' is not available. "
            f"Run 'ollama pull {model}' to download it."
        )


class OllamaAPIError(Exception):
    """Raised when the Ollama API returns an error response."""

    def __init__(self, status_code: int, response_body: str, message: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(
            message
            or f"Ollama API error (status {status_code}): {response_body}"
        )


class OllamaClient:
    """HTTP client for Ollama inference.

    Provides model-routed inference (code vs. reasoning) with
    temperature=0 enforcement, connectivity validation, and
    configurable host/port from environment variables.

    Uses raw HTTP requests to the Ollama API for maximum control
    over request/response handling.
    """

    def __init__(self) -> None:
        # Read configuration from environment variables (OLL-01)
        host = os.getenv("OLLAMA_HOST", "http://localhost")
        port = os.getenv("OLLAMA_PORT", "11434")
        self.base_url = f"{host}:{port}"

        # Timeout for inference requests (default 300s / 5 minutes)
        timeout_str = os.getenv("OLLAMA_TIMEOUT", "300")
        try:
            self.timeout = int(timeout_str)
        except (ValueError, TypeError):
            self.timeout = 300

        # Model routing map (OLL-02, OLL-03)
        self._model_map: dict[str, str] = {
            "code": os.getenv("OLLAMA_CODE_MODEL", "qwen2.5-coder:3b"),
            "reasoning": os.getenv("OLLAMA_REASONING_MODEL", "phi-4-mini:3.8b"),
        }

        logger.info(
            "OllamaClient initialized: base_url=%s, timeout=%ds, models=%s",
            self.base_url,
            self.timeout,
            self._model_map,
        )

    @property
    def code_model(self) -> str:
        """Model used for code understanding tasks (Qwen2.5-Coder 3B)."""
        return self._model_map["code"]

    @property
    def reasoning_model(self) -> str:
        """Model used for reasoning/feedback tasks (Phi-4 Mini)."""
        return self._model_map["reasoning"]

    def validate_connectivity(self) -> dict:
        """Check Ollama connectivity and model availability (OLL-04).

        Sends a GET request to the Ollama /api/tags endpoint to list
        available models, then checks that both required models are present.

        Returns:
            dict: {
                "connected": bool,
                "available_models": list[str],
                "missing_models": list[str]
            }

        Raises:
            OllamaConnectionError: If server is unreachable.
            OllamaModelNotFoundError: If required models are missing.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            raise OllamaConnectionError(
                "Cannot connect to Ollama at "
                f"{self.base_url}. Ensure Ollama is running "
                "(start with 'ollama serve')."
            )
        except requests.exceptions.Timeout:
            raise OllamaConnectionError(
                f"Connection to Ollama at {self.base_url} timed out."
            )
        except requests.exceptions.RequestException as e:
            raise OllamaConnectionError(
                f"Connection to Ollama failed: {e}"
            )

        data = response.json()
        available_models = [m["name"] for m in data.get("models", [])]

        required_models = list(self._model_map.values())
        missing_models = [
            m for m in required_models
            if m not in available_models
        ]

        if missing_models:
            raise OllamaModelNotFoundError(
                model=missing_models[0],
                message=(
                    f"Required Ollama models are missing: {missing_models}. "
                    f"Run the following commands to pull them:\n"
                    + "\n".join(f"  ollama pull {m}" for m in missing_models)
                ),
            )

        return {
            "connected": True,
            "available_models": available_models,
            "missing_models": missing_models,
        }

    def infer(
        self,
        model_role: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        format: Optional[str] = None,
    ) -> dict:
        """Run inference via Ollama with the routed model (OLL-05).

        Args:
            model_role: Either "code" or "reasoning" — routes to the
                appropriate model per OLL-02/OLL-03.
            system_prompt: System-level instruction for the model.
            user_prompt: User query or content to evaluate.
            temperature: Inference temperature. Enforced to 0.0 for
                reproducibility (warns if non-zero passed).
            format: Optional response format ("json" for structured output).

        Returns:
            dict: Parsed response from the model.

        Raises:
            OllamaAPIError: If the API returns an error response.
        """
        # Enforce temperature=0 for reproducibility (OLL-05)
        actual_temperature = 0.0
        if temperature != 0.0:
            logger.warning(
                "Non-zero temperature (%.2f) overridden to 0.0 "
                "for reproducibility (OLL-05).",
                temperature,
            )

        if model_role not in self._model_map:
            raise ValueError(
                f"Unknown model_role '{model_role}'. Must be one of: "
                f"{list(self._model_map.keys())}"
            )

        model = self._model_map[model_role]

        request_body: dict = {
            "model": model,
            "system": system_prompt,
            "prompt": user_prompt,
            "temperature": actual_temperature,
            "stream": False,
        }

        if format is not None:
            request_body["format"] = format

        logger.debug(
            "Ollama infer: model=%s, model_role=%s, temperature=0.0, format=%s",
            model,
            model_role,
            format,
        )

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_body,
                timeout=self.timeout,
            )
        except requests.exceptions.ConnectionError:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url} during inference. "
                "Ensure Ollama is running."
            )
        except requests.exceptions.Timeout:
            raise OllamaAPIError(
                status_code=0,
                response_body=(
                    f"Inference request to {model} timed out after "
                    f"{self.timeout}s."
                ),
            )
        except requests.exceptions.RequestException as e:
            raise OllamaAPIError(
                status_code=0,
                response_body=f"Request failed: {e}",
            )

        if not response.ok:
            raise OllamaAPIError(
                status_code=response.status_code,
                response_body=response.text,
            )

        # Parse the response
        raw_response = response.json()

        if "error" in raw_response:
            raise OllamaAPIError(
                status_code=response.status_code,
                response_body=raw_response["error"],
            )

        response_text = raw_response.get("response", "")

        # If JSON format was requested, try to parse the response as JSON
        if format == "json":
            try:
                result = json.loads(response_text)
                if not isinstance(result, dict):
                    raise OllamaAPIError(
                        status_code=response.status_code,
                        response_body=(
                            f"Expected JSON object response, got {type(result).__name__}"
                        ),
                    )
                return result
            except json.JSONDecodeError as e:
                raise OllamaAPIError(
                    status_code=response.status_code,
                    response_body=(
                        f"Failed to parse model response as JSON: {e}\n"
                        f"Raw response: {response_text[:500]}"
                    ),
                )

        # Plain text response — wrap in dict for consistent return type
        return {"response": response_text}


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    client = OllamaClient()

    try:
        result = client.validate_connectivity()
        if result["connected"]:
            print(f"Ollama connected. Models: {result['available_models']}")
            if result["missing_models"]:
                print(
                    f"WARNING: Missing models: {result['missing_models']}",
                    file=sys.stderr,
                )
                sys.exit(1)
    except OllamaConnectionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except OllamaModelNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
