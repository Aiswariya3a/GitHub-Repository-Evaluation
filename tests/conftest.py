"""Shared pytest fixtures for evaluation pipeline tests.

All fixtures provide in-memory/deterministic data — no external
services (Ollama, PostgreSQL, GitHub) are required.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient that returns controlled responses.
    
    The mock records calls for assertion in tests.
    """
    client = MagicMock()
    client.infer.return_value = {"response": json.dumps({"result": "ok"})}
    client.validate_connectivity.return_value = {
        "connected": True,
        "available_models": ["qwen2.5-coder:3b", "phi-4-mini:3.8b"],
        "missing_models": [],
    }
    return client


@pytest.fixture
def sample_snapshot():
    """Sample ProjectSnapshot dict for testing capability agents."""
    return {
        "repository_metadata": {
            "url": "https://github.com/test/repo",
            "clone_url": "https://github.com/test/repo.git",
            "clone_timestamp": "2026-07-12T00:00:00",
            "status": "success",
            "base_repo_url": None,
        },
        "github_metadata": {
            "commits_count": 10,
            "contributors": [
                {"login": "student1", "contributions": 8},
                {"login": "student2", "contributions": 2},
            ],
            "pull_requests_count": 2,
            "pull_requests": [
                {"number": 1, "title": "Fix bug", "state": "merged"},
            ],
            "issues_count": 3,
            "issues": [
                {"number": 1, "title": "Bug report", "state": "open"},
            ],
        },
        "repo_stats": {
            "total_loc": 500,
            "code_loc": 400,
            "comment_lines": 50,
            "comment_ratio": 0.1,
            "file_count": 5,
            "language_breakdown": {"C": 3, "Python": 2},
        },
        "files": [
            {
                "path": "src/main.c",
                "language": "c",
                "loc": 200,
                "code_loc": 160,
                "functions": [{"name": "main", "lineno": 1, "end_lineno": 50}],
                "classes": [],
                "imports": [
                    {"module": "stdio.h", "names": [], "alias": None},
                ],
                "docstrings": [],
            },
            {
                "path": "src/utils.py",
                "language": "python",
                "loc": 100,
                "code_loc": 80,
                "functions": [{"name": "helper", "lineno": 1, "end_lineno": 20}],
                "classes": [],
                "imports": [
                    {"module": "os", "names": [], "alias": None},
                ],
                "docstrings": ["Helper function docstring"],
            },
        ],
        "delta": None,
        "ingestion_metadata": {
            "version": "1.0",
            "timestamp": "2026-07-12T00:00:00",
            "duration_ms": 1500,
        },
    }


@pytest.fixture
def sample_rubric():
    """Sample rubric config for testing evaluation and aggregation."""
    return {
        "id": "test-rubric-uuid",
        "name": "Test Rubric",
        "description": "A rubric for testing",
        "version": 1,
        "is_default": True,
        "total_score": 8.0,
        "categories": [
            {
                "id": "cat-q1a",
                "code": "Q1A",
                "name": "Compilation and Execution",
                "max_score": 8.0,
                "sort_order": 1,
                "criteria": [
                    {
                        "id": "crit-compile",
                        "criterion_key": "compilation",
                        "name": "Successful Compilation",
                        "max_score": 4.0,
                        "sort_order": 1,
                    },
                    {
                        "id": "crit-exec",
                        "criterion_key": "execution",
                        "name": "Execution Correctness",
                        "max_score": 4.0,
                        "sort_order": 2,
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_criterion_result():
    """Sample individual criterion evaluation result dict."""
    return {
        "criterion_key": "compilation",
        "category_code": "Q1A",
        "score": 3.5,
        "max_score": 4.0,
        "confidence": 0.85,
        "evidence": ["File src/main.c compiles without errors"],
        "remarks": "Good compilation",
    }


@pytest.fixture
def mock_evaluation_repo():
    """Mock EvaluationRepository for tests that need persistence."""
    repo = MagicMock()
    repo.save_evaluation_result.return_value = "eval-result-uuid"
    return repo


@pytest.fixture
def mock_rubric_service(mocker):
    """Mock RubricService returning sample_rubric."""
    svc = mocker.MagicMock()
    svc.default_version_id = "test-rubric-version-id"
    svc.get_version.return_value = {
        "id": "test-rubric-uuid",
        "name": "Test Rubric",
        "version": 1,
        "is_default": True,
        "total_score": 8.0,
        "categories": [
            {
                "id": "cat-q1a",
                "code": "Q1A",
                "name": "Compilation and Execution",
                "max_score": 8.0,
                "sort_order": 1,
                "criteria": [
                    {"id": "crit-compile", "criterion_key": "compilation", "name": "Successful Compilation", "max_score": 4.0, "sort_order": 1},
                    {"id": "crit-exec", "criterion_key": "execution", "name": "Execution Correctness", "max_score": 4.0, "sort_order": 2},
                ],
            }
        ],
    }
    return svc
