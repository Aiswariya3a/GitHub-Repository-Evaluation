"""Deterministic score aggregation — no LLM involved in arithmetic (EVA-06).

Aggregates individual criterion evaluations into category scores and a
final aggregated score. All arithmetic is pure Python with round() to
2 decimal places. Scores are clamped to rubric maximums (EVA-07).
"""

import logging
from typing import Optional

from models.evaluation_models import CriterionEvaluation, CategoryScore, AggregatedScore

logger = logging.getLogger(__name__)


def aggregate_scores(
    criteria_results: list[dict],
    rubric_version: dict,
) -> AggregatedScore:
    """Aggregate individual criterion evaluations into final scores.

    This function is PURELY DETERMINISTIC — no LLM is called during
    aggregation (EVA-06). All arithmetic uses Python built-ins with
    round() to 2 decimal places.

    Args:
        criteria_results: List of validated criterion evaluation dicts
            (each validated against CRITERION_EVALUATION_SCHEMA).
        rubric_version: Rubric version dict from RubricRepository.get_version()
            with structure:
            {
                "categories": [
                    {
                        "code": str,
                        "name": str,
                        "max_score": float,
                        "criteria": [
                            {"criterion_key": str, "name": str, "max_score": float},
                            ...
                        ]
                    },
                    ...
                ],
                "total_score": float
            }

    Returns:
        AggregatedScore with total, normalized_to_20, percentage,
        per-category breakdown, and list of low-confidence criteria.
    """
    # Build lookup: (category_code, criterion_key) -> result dict
    result_map: dict[tuple[str, str], dict] = {}
    for cr in criteria_results:
        key = (cr.get("category_code", ""), cr.get("criterion_key", ""))
        result_map[key] = cr

    categories_list: list[CategoryScore] = []
    total_score = 0.0
    max_score_total = 0.0
    low_conf_criteria: list[str] = []

    for category in rubric_version.get("categories", []):
        cat_code = category.get("code", "")
        cat_name = category.get("name", "Unknown")
        cat_max = float(category.get("max_score", 0))
        max_score_total += cat_max

        criteria_list: list[CriterionEvaluation] = []
        cat_total = 0.0

        for criterion in category.get("criteria", []):
            key = criterion.get("criterion_key", "")
            crit_max = float(criterion.get("max_score", 0))
            result = result_map.get((cat_code, key))

            if result:
                score = float(result.get("score", 0))
                confidence = float(result.get("confidence", 0))
                # Clamp to rubric maximum (EVA-07) — defense-in-depth
                score = max(0.0, min(score, crit_max))

                # Check for low confidence
                is_low_conf = (
                    result.get("confidence_warning", False)
                    or confidence < 0.5
                )
                if is_low_conf:
                    low_conf_criteria.append(f"{cat_code}.{key}")

                criteria_list.append(CriterionEvaluation(
                    criterion_key=key,
                    category_code=cat_code,
                    score=score,
                    max_score=crit_max,
                    confidence=confidence,
                    evidence=result.get("evidence", []),
                    remarks=result.get("remarks", ""),
                    confidence_warning=(confidence < 0.5),
                ))
            else:
                # Missing criterion — score 0 with warning (T-02-04 mitigation)
                low_conf_criteria.append(f"{cat_code}.{key}")
                logger.warning(
                    "Missing criterion evaluation: %s/%s — scored 0",
                    cat_code,
                    key,
                )
                criteria_list.append(CriterionEvaluation(
                    criterion_key=key,
                    category_code=cat_code,
                    score=0.0,
                    max_score=crit_max,
                    confidence=0.0,
                    evidence=[],
                    remarks="Criterion was not evaluated",
                    confidence_warning=True,
                ))

            cat_total += criteria_list[-1].score

        # Clamp category total to category maximum
        cat_total = max(0.0, min(round(cat_total, 2), cat_max))
        total_score += cat_total

        categories_list.append(CategoryScore(
            category_code=cat_code,
            category_name=cat_name,
            total_score=cat_total,
            max_score=cat_max,
            criteria=criteria_list,
        ))

    # Normalize to 20-point scale (standard for this platform)
    if max_score_total > 0:
        normalized = total_score / max_score_total * 20
        percentage = total_score / max_score_total * 100
    else:
        normalized = 0.0
        percentage = 0.0

    return AggregatedScore(
        total_score=round(total_score, 2),
        max_score=round(max_score_total, 2),
        normalized_to_20=round(normalized, 2),
        percentage=round(percentage, 2),
        categories=categories_list,
        low_confidence_criteria=low_conf_criteria,
    )
