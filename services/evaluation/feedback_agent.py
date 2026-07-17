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

Your task is to produce structured feedback by:
1. **Strengths** — Areas where the student performed well (high scores with solid evidence)
2. **Weaknesses** — Areas needing improvement (low scores or low confidence)
3. **Suggestions** — For each weakness, provide a specific, concrete improvement suggestion
4. **Summary** — A brief overall assessment (2-3 sentences)

Rules:
- Do NOT repeat the per-criterion remarks verbatim — synthesize across criteria
- Prioritize: high-impact issues first, minor issues last
- Be constructive — frame weaknesses as opportunities for improvement
- Output ONLY valid JSON with EXACTLY these keys: "strengths", "weaknesses", "suggestions", "summary"

Each strength and weakness item must have EXACTLY these keys: "area", "description"
Each suggestion item must have EXACTLY these keys: "area", "suggestion", "priority" (priority is "high", "medium", or "low")
"summary" is a plain string.

Use lowercase keys exactly as specified above. The full JSON structure must be:
{"strengths": [{"area": "...", "description": "..."}], "weaknesses": [{"area": "...", "description": "..."}], "suggestions": [{"area": "...", "suggestion": "...", "priority": "high|medium|low"}], "summary": "..."}"""

FEEDBACK_USER_PROMPT_TEMPLATE = """Criterion Scores:
{scores_summary}

Category Totals:
{category_summary}

Overall Score: {total_score}/{max_score} ({percentage}%)
Low-Confidence Criteria: {low_conf_list}

Please generate structured feedback based on this data."""

FEEDBACK_RETRY_PROMPT_TEMPLATE = """The previous response was missing the "summary" field. Please fix the response.

The "summary" field is REQUIRED — a plain string of 2-3 sentences providing an overall assessment.

Your complete response MUST have ALL 4 keys:
- "strengths"
- "weaknesses"
- "suggestions"
- "summary"

Previous validation errors:
{validation_errors}

Criterion Scores:
{scores_summary}

Category Totals:
{category_summary}

Overall Score: {total_score}/{max_score} ({percentage}%)
Low-Confidence Criteria: {low_conf_list}

Please generate a complete, valid response."""


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
        if len(scores_summary) > 8000:
            scores_summary = scores_summary[:8000] + "\n... [truncated]"
            logger.warning("scores_summary truncated to 8000 chars")

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

        result = None
        for attempt in range(3):
            try:
                if attempt == 0:
                    current_prompt = user_prompt
                else:
                    err_text = "; ".join(last_errors) if last_errors else "unknown validation errors"
                    current_prompt = FEEDBACK_RETRY_PROMPT_TEMPLATE.format(
                        validation_errors=err_text,
                        scores_summary=scores_summary,
                        category_summary=category_summary,
                        total_score=total_score,
                        max_score=max_score,
                        percentage=percentage,
                        low_conf_list=low_conf_list,
                    )

                raw = self.ollama.infer(
                    model_role="reasoning",
                    system_prompt=FEEDBACK_SYSTEM_PROMPT,
                    user_prompt=current_prompt,
                    format="json",
                )
                result = self._normalize_feedback(raw)
                is_valid, errors = self._validate_output(result, FEEDBACK_SCHEMA)
                if is_valid:
                    break
                else:
                    last_errors = errors
                    result = self._ensure_summary(result)
                    is_valid, errors = self._validate_output(result, FEEDBACK_SCHEMA)
                    if is_valid:
                        break
                    logger.warning(
                        "FeedbackAgent attempt %d: schema validation failed: %s",
                        attempt + 1,
                        "; ".join(errors),
                    )
                    result = None
            except Exception as e:
                last_errors = [str(e)]
                logger.error(
                    "FeedbackAgent attempt %d: error: %s",
                    attempt + 1,
                    str(e),
                )
                result = None

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

        if output_path:
            self._write_output(result, output_path)

        return result

    @staticmethod
    def _normalize_feedback(result: dict) -> dict:
        """Normalize LLM output to conform to FEEDBACK_SCHEMA.

        Handles:
        - Key name variations (e.g. 'Strengths' -> 'strengths')
        - Alternative LLM item structures (e.g. 'Criterion Key' + 'Remarks Synthesis')
        - String items converted to dicts
        - Missing optional fields filled with defaults
        """
        if not isinstance(result, dict):
            return result

        key_map = {
            "strengths": ["strengths", "Strengths", "STRENGTHS", "strength"],
            "weaknesses": ["weaknesses", "Weaknesses", "WEAKNESSES", "weakness"],
            "suggestions": ["suggestions", "Suggestions", "SUGGESTIONS",
                           "suggestion", "actionable suggestions",
                           "Actionable Suggestions", "actionable_suggestions"],
            "summary": ["summary", "Summary", "SUMMARY"],
        }
        normalized = {}
        recognized = False
        for target, aliases in key_map.items():
            for alias in aliases:
                if alias in result:
                    normalized[target] = result[alias]
                    recognized = True
                    break

        if not recognized:
            return result

        for k in ("strengths", "weaknesses"):
            items = normalized.get(k)
            if not isinstance(items, list):
                continue
            rebuilt = []
            for item in items:
                if isinstance(item, str):
                    rebuilt.append({"area": item, "description": "",
                                    "evidence_keys": []})
                    continue
                if not isinstance(item, dict):
                    continue
                alt = ("Criterion Key" in item or "criterion_key" in item or
                       "Confidence Score" in item or "Remarks Synthesis" in item)
                if alt:
                    keys = item.get("Criterion Key", item.get("criterion_key", []))
                    if isinstance(keys, str):
                        keys = [keys]
                    remarks = item.get("Remarks Synthesis",
                                       item.get("remarks_synthesis", ""))
                    rebuilt.append({
                        "area": ", ".join(keys),
                        "description": remarks,
                        "evidence_keys": keys,
                    })
                else:
                    entry = dict(item)
                    ev = entry.get("evidence_keys")
                    if isinstance(ev, str):
                        entry["evidence_keys"] = [ev]
                    elif not isinstance(ev, list):
                        entry["evidence_keys"] = []
                    if "description" not in entry or not entry.get("description"):
                        entry["description"] = entry.pop("priority", entry.pop("remarks", entry.pop("suggestion", "")))
                    rebuilt.append(entry)
            normalized[k] = rebuilt

            # Sanitize evidence_keys — strip null/objects, keep only strings
            for entry in normalized[k]:
                raw = entry.get("evidence_keys", [])
                clean = [str(k) for k in raw if k is not None and isinstance(k, str)]
                entry["evidence_keys"] = clean

        items = normalized.get("suggestions")
        if isinstance(items, list):
            rebuilt = []
            for item in items:
                if isinstance(item, str):
                    rebuilt.append({"area": item, "suggestion": "",
                                    "priority": "medium"})
                    continue
                if not isinstance(item, dict):
                    continue
                alt = ("Criterion Key" in item or "criterion_key" in item or
                       "Suggestion" in item or "suggestion" in item)
                if alt:
                    keys = item.get("Criterion Key", item.get("criterion_key", []))
                    if isinstance(keys, str):
                        keys = [keys]
                    suggestion = item.get("Suggestion", item.get("suggestion", ""))
                    rebuilt.append({
                        "area": ", ".join(keys),
                        "suggestion": suggestion,
                        "priority": item.get("priority", "medium"),
                    })
                else:
                    entry = dict(item)
                    entry.setdefault("priority", "medium")
                    rebuilt.append(entry)
            normalized["suggestions"] = rebuilt

        return normalized

    @staticmethod
    def _ensure_summary(result: dict) -> dict:
        """Ensure 'summary' field exists, synthesizing one from other fields if missing."""
        if "summary" in result and result["summary"]:
            return result
        strengths = result.get("strengths", [])
        weaknesses = result.get("weaknesses", [])
        suggestions = result.get("suggestions", [])
        parts = []
        if strengths:
            parts.append(f"Strengths include {strengths[0].get('area', 'several areas')}")
        if weaknesses:
            parts.append(f"Areas for improvement include {weaknesses[0].get('area', 'several areas')}")
        if suggestions:
            parts.append(f"Key suggestion: {suggestions[0].get('suggestion', 'review the feedback above')}")
        result["summary"] = ". ".join(parts) + "." if parts else "Evaluation complete."
        return result
