"""Unit tests for PipelineService.

All tests use a mocked EvaluationOrchestrator — no real pipeline execution.
No database connection or Ollama instance is required.
"""

from unittest.mock import MagicMock, patch

import pytest

from services.evaluation.pipeline_service import PipelineService


class TestPipelineService:
    """Tests for the high-level pipeline entry point."""

    def test_instantiation_default(self):
        """Test 1: PipelineService creates its own orchestrator."""
        with patch("services.evaluation.pipeline_service.EvaluationOrchestrator"):
            svc = PipelineService()
            assert svc.orchestrator is not None

    def test_instantiation_with_orchestrator(self):
        """Test 2: PipelineService accepts injected orchestrator."""
        mock_orch = MagicMock()
        svc = PipelineService(orchestrator=mock_orch)
        assert svc.orchestrator is mock_orch

    def test_evaluate_repository(self):
        """Test 3: evaluate_repository delegates to orchestrator.evaluate()."""
        mock_orch = MagicMock()
        mock_orch.evaluate.return_value = {
            "pipeline_status": "success",
            "total_score": 7.5,
            "max_score": 8.0,
        }
        svc = PipelineService(orchestrator=mock_orch)
        result = svc.evaluate_repository(
            repo_url="https://github.com/test/repo",
            roll_number="24UCS001",
            session_id="session-1",
            repository_id="repo-1",
        )
        mock_orch.evaluate.assert_called_once_with(
            repo_url="https://github.com/test/repo",
            roll_number="24UCS001",
            session_id="session-1",
            repository_id="repo-1",
            base_repo_url=None,
            rubric_version_id=None,
        )
        assert result["pipeline_status"] == "success"

    def test_evaluate_repository_with_rubric(self):
        """Test 4: evaluate_repository passes rubric_version_id through."""
        mock_orch = MagicMock()
        mock_orch.evaluate.return_value = {"pipeline_status": "success"}
        svc = PipelineService(orchestrator=mock_orch)
        svc.evaluate_repository(
            repo_url="https://github.com/test/repo",
            roll_number="24UCS001",
            session_id="session-1",
            repository_id="repo-1",
            rubric_version_id="rubric-v2",
        )
        mock_orch.evaluate.assert_called_once()
        kwargs = mock_orch.evaluate.call_args[1]
        assert kwargs["rubric_version_id"] == "rubric-v2"

    def test_evaluate_session_empty(self):
        """Test 5: No pending repositories → returns empty list."""
        mock_orch = MagicMock()
        svc = PipelineService(orchestrator=mock_orch)

        with patch("services.repository_service.RepositoryService") as MockRepoService:
            mock_repo_svc = MagicMock()
            mock_repo_svc.pending_repositories.return_value = []
            MockRepoService.return_value = mock_repo_svc

            results = svc.evaluate_session_repositories(session_id="session-1")

            assert results == []
            mock_orch.evaluate.assert_not_called()

    def test_evaluate_session_repositories_basic(self):
        """Test 6: evaluate_session_repositories processes pending repos in order."""
        mock_orch = MagicMock()
        mock_orch.evaluate.side_effect = [
            {"pipeline_status": "success", "total_score": 7.0},
            {"pipeline_status": "partial", "total_score": 5.0},
        ]
        svc = PipelineService(orchestrator=mock_orch)

        with patch("services.repository_service.RepositoryService") as MockRepoService:
            mock_repo_svc = MagicMock()
            mock_repo_svc.pending_repositories.return_value = [
                {"id": "repo-1", "repo_url": "https://github.com/a", "roll_number": "001"},
                {"id": "repo-2", "repo_url": "https://github.com/b", "roll_number": "002"},
            ]
            MockRepoService.return_value = mock_repo_svc

            results = svc.evaluate_session_repositories(session_id="session-1")

            assert len(results) == 2
            assert results[0]["pipeline_status"] == "success"
            assert results[1]["pipeline_status"] == "partial"
            mock_repo_svc.mark_running.assert_called_once_with(
                ["repo-1", "repo-2"]
            )

    def test_evaluate_session_with_error(self):
        """Test 7: Error in one repo doesn't stop processing of others."""
        mock_orch = MagicMock()
        mock_orch.evaluate.side_effect = [
            {"pipeline_status": "success"},
            Exception("Repository error"),
            {"pipeline_status": "success"},
        ]
        svc = PipelineService(orchestrator=mock_orch)

        with patch("services.repository_service.RepositoryService") as MockRepoService:
            mock_repo_svc = MagicMock()
            mock_repo_svc.pending_repositories.return_value = [
                {"id": "repo-1", "repo_url": "https://github.com/a", "roll_number": "001"},
                {"id": "repo-2", "repo_url": "https://github.com/b", "roll_number": "002"},
                {"id": "repo-3", "repo_url": "https://github.com/c", "roll_number": "003"},
            ]
            MockRepoService.return_value = mock_repo_svc

            results = svc.evaluate_session_repositories(session_id="session-1")

            # Failed repo is not added to results (caught in except block)
            assert len(results) == 2  # Only successful repos in results
            assert results[0]["pipeline_status"] == "success"
            assert results[1]["pipeline_status"] == "success"
            # Error repo should have been marked as failed
            mock_repo_svc.mark_failed.assert_called_once_with(
                ["repo-2"], "Repository error"
            )

    def test_evaluate_session_filtered_ids(self):
        """Test 8: repository_ids parameter filters which repos to evaluate."""
        mock_orch = MagicMock()
        svc = PipelineService(orchestrator=mock_orch)

        with patch("services.repository_service.RepositoryService") as MockRepoService:
            mock_repo_svc = MagicMock()
            mock_repo_svc.pending_repositories.return_value = [
                {"id": "repo-1", "repo_url": "https://github.com/a", "roll_number": "001"},
                {"id": "repo-2", "repo_url": "https://github.com/b", "roll_number": "002"},
            ]
            MockRepoService.return_value = mock_repo_svc

            svc.evaluate_session_repositories(
                session_id="session-1", repository_ids=["repo-1"]
            )

            # Should only pass repo-1 to orchestrator
            assert mock_orch.evaluate.call_count == 1
