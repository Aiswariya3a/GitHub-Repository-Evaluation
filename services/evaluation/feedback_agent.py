"""Feedback Agent — generates structured strengths/weaknesses/suggestions from aggregated scores.

Receives all criterion scores with evidence, overall category totals, and
low-confidence flags. Produces categorized feedback: strengths, weaknesses,
actionable suggestions, and a summary.

This agent uses the "reasoning" Ollama model (Phi-4 Mini) for synthesis
and categorization tasks per OLL-03.
"""

import json
import logging
from typing import Optional

from services.evaluation.agent_base import BaseAgent
from services.evaluation.schemas import FEEDBACK_SCHEMA

logger = logging.getLogger(__name__)


FEEDBACK_SYSTEM_PROMPT = """You are a Feedback Generation Agent creating actionable evaluation feedback.

You have been provided with:
- All rubric criterion scores with evidence and remarks (per-criterion mini-feedback already exists per D-05)
- Overall category scores and totals
- Low-confidence flags for uncertain evaluations

Your task is to produce structured feedback by:
1. **Strengths** — Identify areas where the student performed well (high scores with solid evidence)
2. **Weaknesses** — Identify areas needing improvement (low scores or low confidence)
3. **Actionable Suggestions** — For each weakness, provide a specific, concrete improvement suggestion
4. **Summary** — A brief overall assessment (2-3 sentences)

For each strength/weakness/suggestion, reference specific criterion keys as evidence.

Rules:
- Do NOT repeat the per-criterion remarks verbatim — synthesize across criteria (D-07)
- Prioritize: high-impact issues first, minor issues last
- Be constructive — frame weaknesses as opportunities for improvement
- Output ONLY valid JSON matching the feedback schema."""

FEEDBACK_USER_PROMPT_TEMPLATE = """Criterion Scores:
{scores_summary}

Category Totals:
{category_summary}

Overall Score: {total_score}/{max_score} ({percentage}%)
Low-Confidence Criteria: {low_conf_list}

Please generate structured feedback based on this data."""


class FeedbackAgent(BaseAgent):
    """Generates structured feedback from aggregated criterion evaluations.

    Receives the full set of criterion scores, evidence, and remarks, then
    synthesizes them into categorized strengths, weaknesses, actionable
    suggestions, and an overall summary.

    The agent does NOT access PostgreSQL directly — all data is passed in
    via input_data. Retry logic is handled by the orchestrator (ORC-03),
    not the agent.
    """

    def run(
        self,
        input_data: dict,
        output_path: Optional[str] = None,
    ) -> dict:
        """Generate structured feedback from aggregated evaluation results.

        Args:
            input_data: Dict containing:
                - aggregated_result: AggregatedScore dict from score_aggregator
                - criterion_results: list[dict] — raw criterion evaluations
                - low_confidence_criteria: list[str] — criteria with low confidence
            output_path: If provided, writes validated output to this path.

        Returns:
            dict: Validated feedback conforming to FEEDBACK_SCHEMA.
        """
        aggregated_result = input_data.get("aggregated_result", {})
        criterion_results = input_data.get("criterion_results", [])
        low_confidence_criteria = input_data.get("low_confidence_criteria", [])

        # Build scores summary by grouping criteria by category
        scores_lines = []
        categories = aggregated_result.get("categories", [])
        for cat in categories:
            cat_code = cat.get("category_code", "unknown")
            cat_total = cat.get("total_score", 0)
            cat_max = cat.get("max_score", 0)
            scores_lines.append(f"\n{cat_code} ({cat_total}/{cat_max}):")
            for crit in cat.get("criteria", []):
                conf_flag = " ⚠ LOW CONFIDENCE" if crit.get("confidence_warning") else ""
                scores_lines.append(
                    f"  - {crit.get('criterion_key', 'unknown')}: "
                    f"{crit.get('score', 0)}/{crit.get('max_score', 0)} "
                    f"(confidence: {crit.get('confidence', 0)}){conf_flag}"
                )
                evidence_items = crit.get("evidence", [])
                if evidence_items:
                    evidence_preview = "; ".join(str(e) for e in evidence_items[:3])
                    scores_lines.append(f"    Evidence: {evidence_preview}")
                scores_lines.append(f"    Remarks: {crit.get('remarks', '')}")

        scores_summary = "\n".join(scores_lines)
        # Truncate to 8000 chars max to avoid context window overflow
        if len(scores_summary) > 8000:
            scores_summary = scores_summary[:8000] + "\n... [truncated]"
            logger.warning("scores_summary truncated to 8000 chars")

        # Build category summary
        category_lines = []
        for cat in categories:
            category_lines.append(
                f"  {cat.get('category_code', 'unknown')}: "
                f"{cat.get('total_score', 0)}/{cat.get('max_score', 0)}"
            )
        category_summary = "\n".join(category_lines)

        total_score = aggregated_result.get("total_score", 0)
        max_score = aggregated_result.get("max_score", 0)
        percentage = aggregated_result.get("percentage", 0)

        low_conf_list = ", ".join(low_confidence_criteria) if low_confidence_criteria else "None"

        user_prompt = FEEDBACK_USER_PROMPT_TEMPLATE.format(
            scores_summary=scores_summary,
            category_summary=category_summary,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            low_conf_list=low_conf_list,
        )

        logger.info(
            "FeedbackAgent generating feedback: %d categories, %d criteria, %d low-confidence",
            len(categories),
            len(criterion_results),
            len(low_confidence_criteria),
        )

        # Attempt inference with retries for schema validation
        result = None
        for attempt in range(3):
            try:
                result = self.ollama.infer(
                    model_role="reasoning",
                    system_prompt=FEEDBACK_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    format="json",
                )

                # Validate against FEEDBACK_SCHEMA
                is_valid, errors = self._validate_output(result, FEEDBACK_SCHEMA)
                if is_valid:
                    break
                else:
                    logger.warning(
                        "FeedbackAgent attempt %d: schema validation failed: %s",
                        attempt + 1,
                        "; ".join(errors),
                    )
                    result = None
            except Exception as e:
                logger.error(
                    "FeedbackAgent attempt %d: error: %s",
                    attempt + 1,
                    str(e),
                )
                result = None

        # If all attempts failed, return minimal valid result
        if result is None:
            logger.error(
                "FeedbackAgent failed after 3 attempts — returning minimal result"
            )
            result = {
                "strengths": [],
                "weaknesses": [],
                "suggestions": [],
                "summary": "Feedback generation failed after retries",
            }

        # Write output if path provided (D-11)
        if output_path:
            self._write_output(result, output_path)

        return result
