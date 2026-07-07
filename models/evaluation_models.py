"""Dataclasses for evaluation output types.

Defines the type contracts for rubric criterion evaluations, category
scores, and aggregated results. These dataclasses are used across the
evaluation pipeline for type-safe score handling and serialization.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CriterionEvaluation:
    """Per-criterion evaluation result (EVA-03).

    Each rubric criterion evaluation produces one of these, containing
    the score, confidence level, supporting evidence, and remarks/mini-feedback.

    If confidence < 0.5, confidence_warning is set to True (EVA-05).
    """

    criterion_key: str
    category_code: str
    score: float
    max_score: float
    confidence: float
    evidence: list[str]
    remarks: str
    confidence_warning: bool = False


@dataclass
class CategoryScore:
    """Aggregated score for a rubric category.

    Contains the total score for a category along with individual
    criterion evaluations that contributed to it.
    """

    category_code: str
    category_name: str
    total_score: float
    max_score: float
    criteria: list[CriterionEvaluation] = field(default_factory=list)


@dataclass
class AggregatedScore:
    """Top-level aggregated evaluation result (EVA-06, EVA-07).

    Contains the final aggregated scores across all categories,
    normalized to a 20-point scale (standard for this platform),
    percentage, and a list of low-confidence criteria for review.
    """

    total_score: float
    max_score: float
    normalized_to_20: float
    percentage: float
    categories: list[CategoryScore] = field(default_factory=list)
    low_confidence_criteria: list[str] = field(default_factory=list)
