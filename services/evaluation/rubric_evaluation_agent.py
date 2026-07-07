"""Rubric Evaluation Agent — evaluates a single rubric criterion using SLM.

Evaluates ONE criterion per call (EVA-02) using only the evidence routed
to it by the evidence_router. Returns a score, confidence, evidence list,
and remarks (mini-feedback per D-05).

This agent uses the "reasoning" Ollama model (Phi-4 Mini) for
evaluation/scoring tasks per OLL-03.
"""

import json
import logging
from typing import Optional

from services.evaluation.agent_base import BaseAgent
from services.evaluation.schemas import CRITERION_EVALUATION_SCHEMA

logger = logging.getLogger(__name__)

# Maximum evidence text length to avoid context window overflow
MAX_EVIDENCE_CHARS = 8000


RUBRIC_EVALUATION_SYSTEM_PROMPT = """You are a Rubric Evaluation Agent assessing student code against a specific criterion.

You have been provided with:
- A rubric criterion to evaluate (criterion_key, name, max_score)
- Evidence extracted from the student's repository (functions, imports, metrics, etc.)
- The overall repository context (language, file count, complexity)

Your task:
1. Evaluate ONLY the specific criterion using ONLY the provided evidence
2. Assign a score between 0 and max_score (inclusive)
3. Provide a confidence level (0-1) indicating how certain you are
4. List specific evidence items that support your score
5. Write concise, constructive remarks

Rules:
- Be strict but fair — base scores on demonstrated capability
- If evidence is insufficient, score low and note it in remarks
- Confidence < 0.5 means the evidence was unclear or contradictory
- NEVER exceed max_score
- Output ONLY valid JSON matching the schema."""


class RubricEvaluationAgent(BaseAgent):
    """Evaluates a single rubric criterion using SLM inference.

    Processes one criterion per call (EVA-02) with pre-filtered evidence.
    The orchestrator fans out to parallel calls for multiple criteria.

    The agent does NOT access PostgreSQL directly — rubric data is passed
    in via input_data (EVA-01). Retry logic is handled by the orchestrator
    (ORC-03), not the agent.
    """

    def run(
        self,
        input_data: dict,
        output_path: Optional[str] = None,
    ) -> dict:
        """Evaluate a single rubric criterion.

        Args:
            input_data: Dict containing:
                - criterion_key: Unique key for the criterion (e.g., 'Q1A_code_quality')
                - category_code: Rubric category code (e.g., 'Q1A')
                - criterion_name: Human-readable criterion name
                - max_score: Maximum points for this criterion
                - evidence: Pre-filtered snapshot subset from route_evidence()
            output_path: If provided, writes validated output to this path.

        Returns:
            dict: Validated criterion evaluation conforming to
                CRITERION_EVALUATION_SCHEMA.
        """
        criterion_key = input_data.get("criterion_key", "unknown")
        category_code = input_data.get("category_code", "unknown")
        criterion_name = input_data.get("criterion_name", "Unknown criterion")
        max_score = float(input_data.get("max_score", 1.0))
        evidence = input_data.get("evidence", {})

        # Build user prompt
        evidence_str = json.dumps(evidence, indent=2)
        # Truncate evidence to avoid context window overflow (Pitfall 2)
        if len(evidence_str) > MAX_EVIDENCE_CHARS:
            evidence_str = evidence_str[:MAX_EVIDENCE_CHARS] + "\n... [truncated]"
            logger.warning(
                "Evidence for %s/%s truncated to %d chars",
                category_code,
                criterion_key,
                MAX_EVIDENCE_CHARS,
            )

        user_prompt = (
            f"Criterion: {criterion_key} ({criterion_name}) — max {max_score} points\n\n"
            f"Evidence:\n{evidence_str}"
        )

        logger.info(
            "RubricEvaluationAgent evaluating: %s/%s (max_score=%.1f)",
            category_code,
            criterion_key,
            max_score,
        )

        # Call Ollama with "reasoning" model per OLL-03
        result = self.ollama.infer(
            model_role="reasoning",
            system_prompt=RUBRIC_EVALUATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            format="json",
        )

        # Validate against CRITERION_EVALUATION_SCHEMA
        is_valid, errors = self._validate_output(result, CRITERION_EVALUATION_SCHEMA)
        if not is_valid:
            logger.error(
                "RubricEvaluationAgent output failed schema validation "
                "for %s/%s: %s",
                category_code,
                criterion_key,
                "; ".join(errors),
            )
            result = {
                "criterion_key": criterion_key,
                "category_code": category_code,
                "score": 0.0,
                "max_score": max_score,
                "confidence": 0.0,
                "evidence": [],
                "remarks": "Schema validation failed — unable to evaluate criterion.",
            }

        # Clamp score to [0, max_score] (defense-in-depth per T-02-03)
        score = float(result.get("score", 0))
        result["score"] = max(0.0, min(score, max_score))

        # Set confidence_warning if confidence < 0.5 (EVA-05)
        confidence = float(result.get("confidence", 0))
        result["confidence_warning"] = confidence < 0.5

        # Write output if path provided (D-11)
        if output_path:
            self._write_output(result, output_path)

        return result
