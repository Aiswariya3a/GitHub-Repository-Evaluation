"""Unit tests for all 5 evaluation agents.

All tests use mocked OllamaClient — no running Ollama instance required.
"""

import json
from unittest.mock import MagicMock, PropertyMock

import jsonschema
import pytest

from services.evaluation.repo_understanding_agent import RepoUnderstandingAgent
from services.evaluation.code_understanding_agent import CodeUnderstandingAgent
from services.evaluation.collaboration_agent import CollaborationAgent
from services.evaluation.rubric_evaluation_agent import RubricEvaluationAgent
from services.evaluation.feedback_agent import FeedbackAgent
from services.evaluation.schemas import (
    REPO_UNDERSTANDING_SCHEMA,
    CODE_UNDERSTANDING_SCHEMA,
    COLLABORATION_SCHEMA,
    CRITERION_EVALUATION_SCHEMA,
    FEEDBACK_SCHEMA,
)


# ---------------------------------------------------------------------------
# RepoUnderstandingAgent tests
# ---------------------------------------------------------------------------

class TestRepoUnderstandingAgent:
    """Tests for RepoUnderstandingAgent — repository structure analysis."""

    def test_repo_understanding_agent_run(self, mock_ollama_client, sample_snapshot):
        """Agent returns valid repo understanding output matching schema."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "languages": {"C": 3, "Python": 2},
            "key_files": [
                {"path": "src/main.c", "role": "entry point", "importance": "high"},
                {"path": "src/utils.py", "role": "utility module", "importance": "medium"},
            ],
            "total_files": 5,
            "total_loc": 500,
            "structural_summary": "Mixed C and Python project with main entry point.",
            "risk_flags": ["Only 2 source files — may be sparse"],
        }
        agent = RepoUnderstandingAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(sample_snapshot)

        # Assert
        jsonschema.validate(instance=result, schema=REPO_UNDERSTANDING_SCHEMA)
        assert "languages" in result
        assert result["languages"]["C"] == 3
        assert result["languages"]["Python"] == 2
        assert len(result["key_files"]) == 2
        assert result["structural_summary"] != ""
        assert isinstance(result["risk_flags"], list)

    def test_repo_understanding_schema_validation(self, mock_ollama_client, sample_snapshot):
        """Agent output passes schema validation with jsonschema.validate()."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "languages": {"C": 3, "Python": 2},
            "key_files": [
                {"path": "src/main.c", "role": "entry point", "importance": "high"},
            ],
            "total_files": 5,
            "total_loc": 500,
            "structural_summary": "Test summary.",
            "risk_flags": [],
        }
        agent = RepoUnderstandingAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(sample_snapshot)

        # Assert — should not raise ValidationError
        jsonschema.validate(instance=result, schema=REPO_UNDERSTANDING_SCHEMA)

    def test_repo_understanding_schema_fallback(self, mock_ollama_client, sample_snapshot):
        """When schema validation fails, agent returns safe fallback output."""
        mock_ollama_client.infer.return_value = {
            "invalid": "data — missing all required fields"
        }
        agent = RepoUnderstandingAgent(ollama_client=mock_ollama_client)

        result = agent.run(sample_snapshot)

        # Should still validate against schema (fallback is schema-compliant)
        jsonschema.validate(instance=result, schema=REPO_UNDERSTANDING_SCHEMA)
        assert "languages" in result
        assert "Schema validation failed" in result["structural_summary"]


# ---------------------------------------------------------------------------
# CodeUnderstandingAgent tests
# ---------------------------------------------------------------------------

class TestCodeUnderstandingAgent:
    """Tests for CodeUnderstandingAgent — code capability extraction."""

    def test_code_understanding_agent_run(self, mock_ollama_client, sample_snapshot):
        """Agent returns valid code understanding output matching schema."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "capabilities": [
                {
                    "name": "File I/O operations",
                    "description": "Reads and writes files using standard library",
                    "files": ["src/utils.py", "src/main.c"],
                    "confidence": 0.9,
                },
            ],
            "algorithms": ["Bubble sort"],
            "apis": ["stdio.h"],
            "data_structures": ["Array", "Linked list"],
            "file_operations": ["read", "write"],
            "error_handling": {
                "has_error_handling": True,
                "patterns": ["Return code checking", "Exception handling"],
            },
        }
        agent = CodeUnderstandingAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(sample_snapshot)

        # Assert
        jsonschema.validate(instance=result, schema=CODE_UNDERSTANDING_SCHEMA)
        assert len(result["capabilities"]) > 0
        assert result["capabilities"][0]["name"] == "File I/O operations"
        assert result["capabilities"][0]["confidence"] <= 1.0
        assert "error_handling" in result
        assert "has_error_handling" in result["error_handling"]

    def test_code_understanding_empty_snapshot(self, mock_ollama_client):
        """Agent handles snapshot with no files gracefully — returns empty capabilities."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "capabilities": [],
            "algorithms": [],
            "apis": [],
            "data_structures": [],
            "error_handling": {
                "has_error_handling": False,
                "patterns": [],
            },
        }
        empty_snapshot = {
            "files": [],
            "repo_stats": {"total_loc": 0, "code_loc": 0, "file_count": 0, "language_breakdown": {}},
            "delta": None,
        }
        agent = CodeUnderstandingAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(empty_snapshot)

        # Assert
        jsonschema.validate(instance=result, schema=CODE_UNDERSTANDING_SCHEMA)
        assert result["capabilities"] == []
        assert result["algorithms"] == []

    def test_code_understanding_schema_fallback(self, mock_ollama_client, sample_snapshot):
        """When schema validation fails, agent returns safe fallback output."""
        mock_ollama_client.infer.return_value = {"not_valid": True}
        agent = CodeUnderstandingAgent(ollama_client=mock_ollama_client)

        result = agent.run(sample_snapshot)

        jsonschema.validate(instance=result, schema=CODE_UNDERSTANDING_SCHEMA)
        assert "Schema validation failed" in result["capabilities"][0]["name"]


# ---------------------------------------------------------------------------
# CollaborationAgent tests
# ---------------------------------------------------------------------------

class TestCollaborationAgent:
    """Tests for CollaborationAgent — team collaboration analysis."""

    def test_collaboration_agent_run(self, mock_ollama_client, sample_snapshot):
        """Agent returns valid collaboration output matching schema."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "commit_analysis": {
                "total_commits": 10,
                "commit_frequency": "moderate",
                "meaningful_commits": 8,
                "patterns": ["Regular small commits", "Feature branches"],
            },
            "contributor_analysis": {
                "total_contributors": 2,
                "contributions_distribution": "70/30 split",
                "key_contributors": ["student1"],
            },
            "pull_request_analysis": {
                "total_prs": 2,
                "merged_prs": 1,
                "review_quality": "basic",
            },
            "collaboration_score": 0.75,
            "summary": "Good collaboration with balanced contributions.",
        }
        agent = CollaborationAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(sample_snapshot)

        # Assert
        jsonschema.validate(instance=result, schema=COLLABORATION_SCHEMA)
        assert result["commit_analysis"]["total_commits"] == 10
        assert result["collaboration_score"] == 0.75
        assert result["contributor_analysis"]["total_contributors"] == 2
        assert "summary" in result

    def test_collaboration_no_github_metadata(self, mock_ollama_client):
        """Agent handles snapshot with empty github_metadata without crashing."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "commit_analysis": {
                "total_commits": 0,
                "commit_frequency": "none",
                "meaningful_commits": 0,
                "patterns": [],
            },
            "contributor_analysis": {
                "total_contributors": 0,
                "contributions_distribution": "none",
                "key_contributors": [],
            },
            "collaboration_score": 0.0,
            "summary": "No collaboration data available.",
        }
        empty_snapshot = {
            "github_metadata": {},
            "repo_stats": {"total_loc": 0, "file_count": 0},
        }
        agent = CollaborationAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(empty_snapshot)

        # Assert
        jsonschema.validate(instance=result, schema=COLLABORATION_SCHEMA)
        assert result["commit_analysis"]["total_commits"] == 0
        assert result["collaboration_score"] == 0.0


# ---------------------------------------------------------------------------
# RubricEvaluationAgent tests
# ---------------------------------------------------------------------------

class TestRubricEvaluationAgent:
    """Tests for RubricEvaluationAgent — single criterion evaluation."""

    def test_rubric_evaluation_agent_run(self, mock_ollama_client):
        """Agent returns valid criterion evaluation output matching schema."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "criterion_key": "compilation",
            "category_code": "Q1A",
            "score": 3.5,
            "max_score": 4.0,
            "confidence": 0.85,
            "evidence": ["File main.c compiles without errors"],
            "remarks": "Successful compilation with no warnings.",
        }
        input_data = {
            "criterion_key": "compilation",
            "category_code": "Q1A",
            "criterion_name": "Successful Compilation",
            "max_score": 4.0,
            "evidence": {"files": ["src/main.c"]},
        }
        agent = RubricEvaluationAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(input_data)

        # Assert
        jsonschema.validate(instance=result, schema=CRITERION_EVALUATION_SCHEMA)
        assert result["criterion_key"] == "compilation"
        assert result["score"] == 3.5
        assert result["confidence"] == 0.85
        assert not result.get("confidence_warning", False)

    def test_rubric_evaluation_score_clamping(self, mock_ollama_client):
        """Scores exceeding max_score are clamped; negative scores clamped to 0."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "criterion_key": "execution",
            "category_code": "Q1A",
            "score": 10.0,  # exceeds max_score of 4.0
            "max_score": 4.0,
            "confidence": 0.9,
            "evidence": ["Runs correctly"],
            "remarks": "Good execution",
        }
        input_data = {
            "criterion_key": "execution",
            "category_code": "Q1A",
            "criterion_name": "Execution Correctness",
            "max_score": 4.0,
            "evidence": {"files": ["src/main.c"]},
        }
        agent = RubricEvaluationAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(input_data)

        # Assert — score clamped to max_score
        assert result["score"] == 4.0
        assert result["max_score"] == 4.0

        # Test negative score clamping
        mock_ollama_client.infer.return_value = {
            "criterion_key": "execution",
            "category_code": "Q1A",
            "score": -5.0,
            "max_score": 4.0,
            "confidence": 0.9,
            "evidence": ["Runs correctly"],
            "remarks": "Good execution",
        }
        result2 = agent.run(input_data)
        assert result2["score"] == 0.0

    def test_rubric_evaluation_low_confidence(self, mock_ollama_client):
        """Confidence < 0.5 sets confidence_warning=True."""
        mock_ollama_client.infer.return_value = {
            "criterion_key": "compilation",
            "category_code": "Q1A",
            "score": 2.0,
            "max_score": 4.0,
            "confidence": 0.3,
            "evidence": ["Partial compilation"],
            "remarks": "Some issues found",
        }
        input_data = {
            "criterion_key": "compilation",
            "category_code": "Q1A",
            "criterion_name": "Successful Compilation",
            "max_score": 4.0,
            "evidence": {},
        }
        agent = RubricEvaluationAgent(ollama_client=mock_ollama_client)

        result = agent.run(input_data)

        assert result["confidence_warning"] is True
        assert result["confidence"] == 0.3


# ---------------------------------------------------------------------------
# FeedbackAgent tests
# ---------------------------------------------------------------------------

class TestFeedbackAgent:
    """Tests for FeedbackAgent — structured feedback generation."""

    def test_feedback_agent_run(self, mock_ollama_client):
        """Agent returns valid feedback output matching schema."""
        # Arrange
        mock_ollama_client.infer.return_value = {
            "strengths": [
                {
                    "area": "Compilation",
                    "description": "Code compiles without errors",
                    "evidence_keys": ["Q1A.compilation"],
                },
            ],
            "weaknesses": [
                {
                    "area": "Documentation",
                    "description": "Limited docstrings and comments",
                    "evidence_keys": ["Q1A.execution"],
                },
            ],
            "suggestions": [
                {
                    "area": "Documentation",
                    "suggestion": "Add docstrings to all functions",
                    "priority": "medium",
                },
            ],
            "summary": "Good compilation but needs better documentation.",
        }
        input_data = {
            "aggregated_result": {
                "total_score": 6.0,
                "max_score": 8.0,
                "normalized_to_20": 15.0,
                "percentage": 75.0,
                "categories": [
                    {
                        "category_code": "Q1A",
                        "category_name": "Compilation and Execution",
                        "total_score": 6.0,
                        "max_score": 8.0,
                        "criteria": [
                            {
                                "criterion_key": "compilation",
                                "category_code": "Q1A",
                                "score": 3.5,
                                "max_score": 4.0,
                                "confidence": 0.85,
                                "evidence": ["Compiles ok"],
                                "remarks": "Good",
                                "confidence_warning": False,
                            },
                            {
                                "criterion_key": "execution",
                                "category_code": "Q1A",
                                "score": 2.5,
                                "max_score": 4.0,
                                "confidence": 0.6,
                                "evidence": ["Runs ok"],
                                "remarks": "OK",
                                "confidence_warning": False,
                            },
                        ],
                    },
                ],
                "low_confidence_criteria": [],
            },
            "criterion_results": [],
            "low_confidence_criteria": [],
        }
        agent = FeedbackAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(input_data)

        # Assert
        jsonschema.validate(instance=result, schema=FEEDBACK_SCHEMA)
        assert len(result["strengths"]) > 0
        assert len(result["weaknesses"]) > 0
        assert len(result["suggestions"]) > 0
        assert result["summary"] != ""
        assert "priority" in result["suggestions"][0]
        assert result["suggestions"][0]["priority"] in ("high", "medium", "low")

    def test_feedback_agent_partial_failure(self, mock_ollama_client):
        """When all infer() attempts fail, agent returns minimal valid output."""
        # Make all 3 attempts fail by returning invalid data
        mock_ollama_client.infer.return_value = {"bad": "data — missing required fields"}
        input_data = {
            "aggregated_result": {
                "total_score": 0,
                "max_score": 8.0,
                "normalized_to_20": 0,
                "percentage": 0,
                "categories": [],
                "low_confidence_criteria": [],
            },
            "criterion_results": [],
            "low_confidence_criteria": [],
        }
        agent = FeedbackAgent(ollama_client=mock_ollama_client)

        # Act
        result = agent.run(input_data)

        # Assert — minimal valid result returned
        jsonschema.validate(instance=result, schema=FEEDBACK_SCHEMA)
        assert result["strengths"] == []
        assert result["weaknesses"] == []
        assert result["suggestions"] == []
        assert "failed" in result["summary"].lower()

    def test_feedback_agent_empty_strengths_weaknesses(self, mock_ollama_client):
        """Agent handles case with no strengths or weaknesses gracefully."""
        mock_ollama_client.infer.return_value = {
            "strengths": [],
            "weaknesses": [],
            "suggestions": [],
            "summary": "No evaluation data available.",
        }
        input_data = {
            "aggregated_result": {
                "total_score": 0,
                "max_score": 0,
                "normalized_to_20": 0,
                "percentage": 0,
                "categories": [],
                "low_confidence_criteria": [],
            },
            "criterion_results": [],
            "low_confidence_criteria": [],
        }
        agent = FeedbackAgent(ollama_client=mock_ollama_client)

        result = agent.run(input_data)

        jsonschema.validate(instance=result, schema=FEEDBACK_SCHEMA)
        assert result["strengths"] == []
        assert result["weaknesses"] == []
        assert result["summary"] != ""
