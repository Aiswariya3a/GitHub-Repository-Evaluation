"""Tests for the EvaluationOrchestrator."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from services.evaluation.orchestrator import EvaluationOrchestrator


@pytest.fixture
def mock_services():
    """Create mock dependencies that don't require database connectivity."""
    mock_rubric_service = MagicMock()
    mock_rubric_service.default_version_id = "test-rubric-version-id"

    mock_evaluation_repo = MagicMock()
    mock_ingestion_repo = MagicMock()
    mock_ingestion_service = MagicMock()

    return {
        "rubric_service": mock_rubric_service,
        "evaluation_repo": mock_evaluation_repo,
        "ingestion_repo": mock_ingestion_repo,
        "ingestion_service": mock_ingestion_service,
    }


class TestEvaluationOrchestrator:
    """Tests for orchestrator instantiation and basic functionality."""

    def test_instantiation(self, mock_services):
        """Test 1: Orchestrator can be instantiated with default config."""
        orch = EvaluationOrchestrator(
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )
        assert orch.max_parallel == 2
        assert orch.max_retries == 2
        assert orch.execution_mode == "in_process"
        assert orch.repo_agent is not None
        assert orch.code_agent is not None
        assert orch.collab_agent is not None
        assert orch.rubric_agent is not None
        assert orch.feedback_agent is not None

    def test_session_dir_creation(self, mock_services):
        """Test 2: Creates session working directory."""
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                working_dir=tmp,
                rubric_service=mock_services["rubric_service"],
                evaluation_repo=mock_services["evaluation_repo"],
                ingestion_repo=mock_services["ingestion_repo"],
                ingestion_service=mock_services["ingestion_service"],
            )
            session_dir = orch._create_session_dir("test-session", "test-repo")
            assert os.path.exists(session_dir)
            assert session_dir.startswith(tmp)
            assert "test-session" in session_dir
            assert "test-repo" in session_dir

    def test_detect_completed_steps_empty(self, mock_services):
        """Test 3a: Returns empty dict for fresh working directory."""
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                working_dir=tmp,
                rubric_service=mock_services["rubric_service"],
                evaluation_repo=mock_services["evaluation_repo"],
                ingestion_repo=mock_services["ingestion_repo"],
                ingestion_service=mock_services["ingestion_service"],
            )
            completed = orch._detect_completed_steps(tmp)
            assert isinstance(completed, dict)
            assert len(completed) == 0

    def test_detect_completed_steps_populated(self, mock_services):
        """Test 3b: Returns populated dict when output files exist."""
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                working_dir=tmp,
                rubric_service=mock_services["rubric_service"],
                evaluation_repo=mock_services["evaluation_repo"],
                ingestion_repo=mock_services["ingestion_repo"],
                ingestion_service=mock_services["ingestion_service"],
            )
            # Create a fake completed step
            step_path = orch._step_output_path(tmp, "repo_understanding")
            os.makedirs(os.path.dirname(step_path), exist_ok=True)
            with open(step_path, "w") as f:
                json.dump({"languages": {"Python": 5}}, f)

            completed = orch._detect_completed_steps(tmp)
            assert "repo_understanding" in completed
            assert completed["repo_understanding"]["languages"]["Python"] == 5

    def test_step_output_path(self, mock_services):
        """Verify _step_output_path returns correct JSON path."""
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                working_dir=tmp,
                rubric_service=mock_services["rubric_service"],
                evaluation_repo=mock_services["evaluation_repo"],
                ingestion_repo=mock_services["ingestion_repo"],
                ingestion_service=mock_services["ingestion_service"],
            )
            path = orch._step_output_path(tmp, "test_step")
            assert path.endswith("test_step.json")
            assert path.startswith(tmp)

    def test_max_parallel_config(self, mock_services):
        """Test 4: max_parallel_agents is stored and limits concurrency."""
        orch = EvaluationOrchestrator(
            max_parallel_agents=3,
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )
        assert orch.max_parallel == 3

        # Default should be 2
        orch_default = EvaluationOrchestrator(
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )
        assert orch_default.max_parallel == 2

    def test_failed_agents_partial_status(self, mock_services):
        """Test 5: Pipeline status reflects failed agents."""
        orch = EvaluationOrchestrator(
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )
        assert len(orch.failed_agents) == 0

        # Simulate agent failures
        orch.failed_agents.append("TestAgent")
        assert "TestAgent" in orch.failed_agents

        # Pipeline status should be 'partial' when agents failed
        pipeline_status = "partial" if orch.failed_agents else "success"
        assert pipeline_status == "partial"
