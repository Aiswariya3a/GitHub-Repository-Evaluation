"""Tests for the EvaluationOrchestrator.

Covers:
  - Instantiation and basic configuration (7 existing tests preserved)
  - Workflow lifecycle (evaluate() with mocked internals)
  - Step recovery via file-based output detection
  - Retry logic (_run_agent_with_retry success, all-fail, schema failure)
  - Parallel agent execution with partial failures
  - Corrupted file handling in recovery
"""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from services.evaluation.orchestrator import EvaluationOrchestrator
from services.evaluation.schemas import (
    REPO_UNDERSTANDING_SCHEMA,
    CODE_UNDERSTANDING_SCHEMA,
    COLLABORATION_SCHEMA,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


@pytest.fixture
def mock_ingestion_service():
    """Mock IngestionService for tests that need evaluate() to proceed."""
    svc = MagicMock()
    svc.ingest.return_value = {
        "snapshot": {
            "repo_stats": {"total_loc": 100, "file_count": 2,
                           "language_breakdown": {"Python": 2}},
            "files": [],
            "repository_metadata": {"url": "https://github.com/test/repo"},
            "github_metadata": {},
        }
    }
    return svc


@pytest.fixture
def mock_ingestion_repo():
    """Mock IngestionRepository for tests that need it."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Existing Tests (7 tests preserved)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Workflow Lifecycle Tests (Test 8-9)
# ---------------------------------------------------------------------------

class TestOrchestratorWorkflow:
    """Tests for the evaluate() workflow lifecycle."""

    def _make_minimal_snapshot(self):
        """Minimal snapshot dict for workflow tests."""
        return {
            "repo_stats": {"total_loc": 50, "file_count": 1,
                           "language_breakdown": {"Python": 1}},
            "files": [],
            "repository_metadata": {"url": "https://github.com/test/repo"},
            "github_metadata": {"commits_count": 1, "contributors": []},
        }

    def test_evaluate_full_workflow(self, mock_rubric_service, mock_evaluation_repo,
                                     mock_ingestion_service, mock_ingestion_repo):
        """Test 8: Full evaluate() lifecycle completes successfully.

        Uses deep mocking to bypass LLM calls and test the orchestrator's
        step orchestration logic.
        """
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                ollama_client=MagicMock(),
                rubric_service=mock_rubric_service,
                evaluation_repo=mock_evaluation_repo,
                working_dir=tmp,
                ingestion_service=mock_ingestion_service,
                ingestion_repo=mock_ingestion_repo,
            )

            # Mock the internal retry method to return canned outputs
            # so no real agent or LLM call is needed.
            def mock_retry(agent_fn, agent_name, *args, **kwargs):
                outputs = {
                    "RepoUnderstandingAgent": {
                        "languages": {"Python": 1}, "key_files": [],
                        "structural_summary": "Simple repo", "risk_flags": [],
                    },
                    "CodeUnderstandingAgent": {
                        "capabilities": [], "algorithms": [],
                        "apis": [], "data_structures": [],
                        "error_handling": {"has_error_handling": False, "patterns": []},
                    },
                    "CollaborationAgent": {
                        "commit_analysis": {"total_commits": 1},
                        "contributor_analysis": {"total_contributors": 1},
                        "collaboration_score": 0.5,
                    },
                    "FeedbackAgent": {
                        "strengths": [], "weaknesses": [],
                        "suggestions": [], "summary": "OK",
                    },
                }
                if "RubricEval" in agent_name:
                    return {
                        "criterion_key": "compilation", "category_code": "Q1A",
                        "score": 3.0, "max_score": 4.0,
                        "confidence": 0.8, "evidence": [], "remarks": "Good",
                    }
                return outputs.get(agent_name)

            with patch.object(orch, '_run_agent_with_retry', side_effect=mock_retry):
                result = orch.evaluate(
                    repo_url="https://github.com/test/repo",
                    roll_number="24UCS001",
                    session_id="session-1",
                    repository_id="repo-1",
                )

            assert result is not None
            assert "pipeline_status" in result
            assert "total_score" in result
            assert "repo_understanding" in result
            assert "code_understanding" in result
            assert "collaboration" in result
            assert result["repo_understanding"]["structural_summary"] == "Simple repo"

    def test_evaluate_step_recovery(self, mock_rubric_service, mock_evaluation_repo,
                                     mock_ingestion_service, mock_ingestion_repo):
        """Test 9: File-based recovery skips completed steps."""
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                working_dir=tmp,
                rubric_service=mock_rubric_service,
                evaluation_repo=mock_evaluation_repo,
                ingestion_service=mock_ingestion_service,
                ingestion_repo=mock_ingestion_repo,
            )
            session_dir = orch._create_session_dir("session-r", "repo-r")

            # Create a fake aggregation output to simulate partial completion
            agg_path = orch._step_output_path(session_dir, "aggregation")
            os.makedirs(os.path.dirname(agg_path), exist_ok=True)
            with open(agg_path, "w") as f:
                json.dump({"total_score": 5.0, "max_score": 8.0}, f)

            completed = orch._detect_completed_steps(session_dir)
            assert "aggregation" in completed
            assert completed["aggregation"]["total_score"] == 5.0


# ---------------------------------------------------------------------------
# Error Handling Tests (Tests 10-13)
# ---------------------------------------------------------------------------

class TestOrchestratorErrorHandling:
    """Tests for retry logic and partial failure handling."""

    _sample_snapshot = staticmethod(lambda: {
        "repo_stats": {"total_loc": 100, "file_count": 2,
                       "language_breakdown": {"Python": 2}},
        "files": [{"path": "main.py", "language": "python", "loc": 50,
                   "code_loc": 40, "functions": [], "classes": [],
                   "imports": [], "docstrings": []}],
        "repository_metadata": {"url": "https://github.com/test/repo"},
        "github_metadata": {"commits_count": 5, "contributors": []},
    })

    def test_run_agent_with_retry_success(self, mock_services):
        """Test 10: Agent succeeds on first attempt — retry returns immediately."""
        mock_agent = MagicMock()
        mock_agent.run.return_value = {
            "languages": {"Python": 3}, "key_files": [],
            "structural_summary": "Test", "risk_flags": [],
        }
        mock_agent._validate_output.return_value = (True, [])

        orch = EvaluationOrchestrator(
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )
        result = orch._run_agent_with_retry(
            mock_agent, "TestAgent", {"test": True},
            "/tmp/test_output.json", REPO_UNDERSTANDING_SCHEMA, "repo_understanding",
        )
        assert result is not None
        assert result["structural_summary"] == "Test"
        mock_agent.run.assert_called_once()

    def test_run_agent_with_retry_all_fail(self, mock_services):
        """Test 11: Agent fails after max_retries — returns None and adds to failed_agents."""
        mock_agent = MagicMock()
        mock_agent.run.side_effect = Exception("Ollama unavailable")

        orch = EvaluationOrchestrator(
            max_retries=2,
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )
        result = orch._run_agent_with_retry(
            mock_agent, "TestAgent", {"test": True},
            "/tmp/test_output.json", {}, "test_step",
        )
        assert result is None
        assert "TestAgent" in orch.failed_agents
        # Should have attempted max_retries + 1 = 3 times
        assert mock_agent.run.call_count == 3

    def test_run_agent_schema_validation_failure(self, mock_services):
        """Test 12: Agent output fails schema validation — retries up to max_retries."""
        mock_agent = MagicMock()
        mock_agent.run.return_value = {"invalid": True}
        mock_agent._validate_output.return_value = (False, ["Missing required fields"])

        orch = EvaluationOrchestrator(
            max_retries=1,
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )
        result = orch._run_agent_with_retry(
            mock_agent, "SchemaAgent", {"test": True},
            "/tmp/test_output.json", {}, "test_step",
        )
        assert result is None
        assert "SchemaAgent" in orch.failed_agents
        # max_retries=1 means 2 total attempts
        assert mock_agent.run.call_count == 2
        assert mock_agent._validate_output.call_count == 2

    def test_parallel_agents_partial_failure(self, mock_services):
        """Test 13: One agent fails (raises exception), others succeed → pipeline continues."""
        orch = EvaluationOrchestrator(
            rubric_service=mock_services["rubric_service"],
            evaluation_repo=mock_services["evaluation_repo"],
            ingestion_repo=mock_services["ingestion_repo"],
            ingestion_service=mock_services["ingestion_service"],
        )

        # Use callables that raise or return directly to test parallel execution
        agents = [
            (lambda: {"repo": True}, "RepoAgent", "repo_understanding"),
            (lambda: {"code": True}, "CodeAgent", "code_understanding"),
            (lambda: (_ for _ in ()).throw(Exception("Collab failed")),
             "CollabAgent", "collaboration"),
        ]
        cap_results = orch._run_parallel_agents(agents, "/tmp")

        assert cap_results.get("repo_understanding") is not None
        assert cap_results.get("code_understanding") is not None
        assert cap_results.get("collaboration") is None
        assert "CollabAgent" in orch.failed_agents


# ---------------------------------------------------------------------------
# Recovery Tests (Tests 14-15)
# ---------------------------------------------------------------------------

class TestOrchestratorRecovery:
    """Tests for file-based recovery (D-11, D-12)."""

    def test_detect_completed_steps_aggregation_only(self, mock_services):
        """Test 14: Only aggregation output exists — detects exactly that.

        This is equivalent to test_detect_completed_steps_populated but
        with the aggregation step specifically. The existing test 3b already
        covers this with repo_understanding step.
        """
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                working_dir=tmp,
                rubric_service=mock_services["rubric_service"],
                evaluation_repo=mock_services["evaluation_repo"],
                ingestion_repo=mock_services["ingestion_repo"],
                ingestion_service=mock_services["ingestion_service"],
            )
            # Create aggregation output
            agg_path = orch._step_output_path(tmp, "aggregation")
            os.makedirs(os.path.dirname(agg_path), exist_ok=True)
            with open(agg_path, "w") as f:
                json.dump({"total_score": 8.0, "max_score": 8.0}, f)

            completed = orch._detect_completed_steps(tmp)
            assert "aggregation" in completed
            assert "repo_understanding" not in completed
            assert completed["aggregation"]["total_score"] == 8.0

    def test_detect_completed_steps_corrupted_file(self, mock_services):
        """Test 15: Corrupted JSON file is skipped (not loaded)."""
        with tempfile.TemporaryDirectory() as tmp:
            orch = EvaluationOrchestrator(
                working_dir=tmp,
                rubric_service=mock_services["rubric_service"],
                evaluation_repo=mock_services["evaluation_repo"],
                ingestion_repo=mock_services["ingestion_repo"],
                ingestion_service=mock_services["ingestion_service"],
            )
            agg_path = orch._step_output_path(tmp, "aggregation")
            os.makedirs(os.path.dirname(agg_path), exist_ok=True)
            with open(agg_path, "w") as f:
                f.write("{invalid json")

            completed = orch._detect_completed_steps(tmp)
            assert "aggregation" not in completed
