"""Unit tests for aggregate_scores() — deterministic score aggregation.

All tests exercise the pure arithmetic logic in score_aggregator.py.
No LLM or external services are involved.
"""

import pytest

from services.evaluation.score_aggregator import aggregate_scores
from models.evaluation_models import AggregatedScore


def _make_rubric(categories: list[dict]) -> dict:
    """Build a minimal rubric_version dict."""
    return {
        "id": "test-rubric",
        "name": "Test Rubric",
        "version": 1,
        "is_default": True,
        "total_score": sum(c.get("max_score", 0) for c in categories),
        "categories": categories,
    }


def _make_criterion_result(
    criterion_key: str,
    category_code: str,
    score: float,
    max_score: float = 4.0,
    confidence: float = 0.9,
    evidence: list | None = None,
    remarks: str = "OK",
    confidence_warning: bool = False,
) -> dict:
    """Build a criterion evaluation result dict."""
    return {
        "criterion_key": criterion_key,
        "category_code": category_code,
        "score": score,
        "max_score": max_score,
        "confidence": confidence,
        "evidence": evidence or ["Evidence item"],
        "remarks": remarks,
        "confidence_warning": confidence_warning,
    }


class TestAggregateBasic:
    """Basic aggregation scenarios."""

    def test_aggregate_basic(self):
        """Two criteria with full scores → correct total, percentage, normalized."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 8.0,
                "criteria": [
                    {"criterion_key": "compilation", "name": "Compilation Success", "max_score": 4.0},
                    {"criterion_key": "execution", "name": "Execution Correctness", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", 4.0, max_score=4.0),
            _make_criterion_result("execution", "Q1A", 4.0, max_score=4.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert isinstance(agg, AggregatedScore)
        assert agg.total_score == 8.0
        assert agg.max_score == 8.0
        assert agg.percentage == 100.0
        assert agg.normalized_to_20 == 20.0
        assert len(agg.categories) == 1
        assert agg.categories[0].total_score == 8.0
        assert agg.categories[0].max_score == 8.0

    def test_aggregate_partial_scores(self):
        """Partial scores produce correct proportional results."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 8.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                    {"criterion_key": "execution", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", 3.0, max_score=4.0),
            _make_criterion_result("execution", "Q1A", 2.0, max_score=4.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.total_score == 5.0
        assert agg.percentage == 62.5  # 5/8 * 100
        assert agg.normalized_to_20 == 12.5  # 5/8 * 20
        assert agg.categories[0].total_score == 5.0


class TestAggregateMissingCriteria:
    """Scenarios where criteria evaluations are missing."""

    def test_aggregate_missing_criterion(self):
        """One criterion missing → scored 0 with confidence_warning."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 8.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                    {"criterion_key": "execution", "max_score": 4.0},
                ],
            },
        ])
        # Only provide one criterion result — execution is missing
        results = [
            _make_criterion_result("compilation", "Q1A", 3.0, max_score=4.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.total_score == 3.0  # execution scored 0
        assert len(agg.categories[0].criteria) == 2
        # Missing criterion should have confidence_warning
        missing = agg.categories[0].criteria[1]
        assert missing.criterion_key == "execution"
        assert missing.score == 0.0
        assert missing.confidence_warning is True

    def test_aggregate_all_criteria_missing(self):
        """All criteria missing → all zeros, all confidence_warnings."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 8.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                    {"criterion_key": "execution", "max_score": 4.0},
                ],
            },
        ])
        results = []

        agg = aggregate_scores(results, rubric)

        assert agg.total_score == 0.0
        assert agg.percentage == 0.0
        assert agg.normalized_to_20 == 0.0
        assert len(agg.low_confidence_criteria) == 2
        for criterion in agg.categories[0].criteria:
            assert criterion.score == 0.0
            assert criterion.confidence_warning is True


class TestAggregateScoreClamping:
    """Score clamping behavior (EVA-07)."""

    def test_aggregate_score_clamping(self):
        """Score exceeding max_score → clamped to max."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 4.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", 10.0, max_score=4.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.categories[0].criteria[0].score == 4.0  # clamped to max
        assert agg.total_score == 4.0

    def test_aggregate_negative_score_clamping(self):
        """Negative score → clamped to 0."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 4.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", -5.0, max_score=4.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.categories[0].criteria[0].score == 0.0
        assert agg.total_score == 0.0

    def test_aggregate_category_total_clamping(self):
        """Category total cannot exceed category max_score even if criteria sum exceeds it."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 6.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                    {"criterion_key": "execution", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", 4.0, max_score=4.0),
            _make_criterion_result("execution", "Q1A", 4.0, max_score=4.0),
        ]
        # Criteria sum = 8.0, but category max = 6.0

        agg = aggregate_scores(results, rubric)

        assert agg.categories[0].total_score == 6.0  # clamped
        assert agg.total_score == 6.0


class TestAggregateLowConfidence:
    """Low confidence detection (EVA-05)."""

    def test_aggregate_low_confidence_detection(self):
        """Confidence < 0.5 → added to low_confidence_criteria."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 8.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                    {"criterion_key": "execution", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", 3.0, max_score=4.0, confidence=0.3),
            _make_criterion_result("execution", "Q1A", 4.0, max_score=4.0, confidence=0.9),
        ]

        agg = aggregate_scores(results, rubric)

        assert "Q1A.compilation" in agg.low_confidence_criteria
        assert "Q1A.execution" not in agg.low_confidence_criteria
        assert len(agg.low_confidence_criteria) == 1

    def test_aggregate_confidence_warning_flag(self):
        """confidence_warning=True in result also triggers low confidence listing."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 4.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result(
                "compilation", "Q1A", 3.0, max_score=4.0,
                confidence=0.8,  # high confidence
                confidence_warning=True,  # but warning flag set by agent
            ),
        ]

        agg = aggregate_scores(results, rubric)

        assert "Q1A.compilation" in agg.low_confidence_criteria


class TestAggregateEdgeCases:
    """Edge cases: empty, zero, missing data."""

    def test_aggregate_empty_criteria(self):
        """Empty criteria list → all zeros, no crash."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 8.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                    {"criterion_key": "execution", "max_score": 4.0},
                ],
            },
        ])
        results = []

        agg = aggregate_scores(results, rubric)

        assert agg.total_score == 0.0
        assert agg.percentage == 0.0
        assert agg.normalized_to_20 == 0.0
        assert isinstance(agg, AggregatedScore)

    def test_aggregate_no_rubric_categories(self):
        """Rubric with no categories → handles gracefully."""
        rubric = _make_rubric([])
        results = [
            _make_criterion_result("compilation", "Q1A", 3.0, max_score=4.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.total_score == 0.0
        assert agg.max_score == 0.0
        assert agg.percentage == 0.0
        assert agg.normalized_to_20 == 0.0
        assert len(agg.categories) == 0

    def test_aggregate_zero_max_score(self):
        """max_score_total = 0 → normalized = 0, percentage = 0 (no division by zero)."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 0.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 0.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", 0.0, max_score=0.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.max_score == 0.0
        assert agg.total_score == 0.0
        assert agg.percentage == 0.0
        assert agg.normalized_to_20 == 0.0

    def test_aggregate_normalization(self):
        """total_score/max_score * 20 = normalized_to_20, max_score > 0."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Test",
                "max_score": 10.0,
                "criteria": [
                    {"criterion_key": "test", "max_score": 10.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("test", "Q1A", 7.5, max_score=10.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.normalized_to_20 == 15.0  # 7.5/10 * 20
        assert agg.percentage == 75.0

    def test_aggregate_multiple_categories(self):
        """Multiple categories aggregated correctly."""
        rubric = _make_rubric([
            {
                "code": "Q1A",
                "name": "Compilation",
                "max_score": 8.0,
                "criteria": [
                    {"criterion_key": "compilation", "max_score": 4.0},
                    {"criterion_key": "execution", "max_score": 4.0},
                ],
            },
            {
                "code": "Q1B",
                "name": "Documentation",
                "max_score": 4.0,
                "criteria": [
                    {"criterion_key": "docstrings", "max_score": 4.0},
                ],
            },
        ])
        results = [
            _make_criterion_result("compilation", "Q1A", 4.0, max_score=4.0),
            _make_criterion_result("execution", "Q1A", 3.0, max_score=4.0),
            _make_criterion_result("docstrings", "Q1B", 2.0, max_score=4.0),
        ]

        agg = aggregate_scores(results, rubric)

        assert agg.total_score == 9.0  # 7 + 2
        assert agg.max_score == 12.0  # 8 + 4
        assert len(agg.categories) == 2
        assert agg.categories[0].total_score == 7.0
        assert agg.categories[1].total_score == 2.0
        assert pytest.approx(agg.percentage, 0.01) == 75.0  # 9/12 * 100
