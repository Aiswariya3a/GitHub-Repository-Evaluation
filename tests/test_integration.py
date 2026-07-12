"""Full pipeline integration test.

Runs the complete evaluation pipeline end-to-end:
ingestion → capability agents → rubric evaluation → feedback → persistence.

This test requires:
- A running Ollama instance with qwen2.5-coder:3b and phi-4-mini:3.8b
- A real public GitHub repository URL
- PostgreSQL connection (DATABASE_URL env var)

Skip with: pytest -m "not integration"
"""

import os

import pytest

# Integration tests are opt-in — skip by default
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require RUN_INTEGRATION_TESTS=1, Ollama, and PostgreSQL"
)


@pytest.mark.integration
class TestFullPipeline:
    """End-to-end pipeline integration test."""

    REPO_URL = os.environ.get(
        "TEST_REPO_URL",
        "https://github.com/24UCS271-MiniProject/miniProjectSourceCode"
    )
    ROLL_NUMBER = "TEST-INTEGRATION-001"

    @pytest.fixture
    def pipeline_config(self):
        """Create a lightweight PipelineService for integration testing."""
        from services.evaluation.pipeline_service import PipelineService

        # Validate Ollama availability before running
        from services.ollama_client import OllamaClient
        client = OllamaClient()
        connectivity = client.validate_connectivity()
        assert connectivity["connected"], (
            f"Ollama not available. Start Ollama and pull required models.\n"
            f"Missing models: {connectivity.get('missing_models', [])}"
        )

        return PipelineService()

    def test_full_pipeline_evaluation(self, pipeline_config):
        """Test 1: Complete pipeline produces valid evaluation results."""
        import uuid
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        repository_id = f"test-repo-{uuid.uuid4().hex[:8]}"

        result = pipeline_config.evaluate_repository(
            repo_url=self.REPO_URL,
            roll_number=self.ROLL_NUMBER,
            session_id=session_id,
            repository_id=repository_id,
        )

        # Verify pipeline completed
        assert result is not None
        assert result.get("pipeline_status") in ("success", "partial"), (
            f"Pipeline failed: {result.get('error')}"
        )

        # Verify capability outputs
        assert "repo_understanding" in result
        assert "code_understanding" in result
        assert "collaboration" in result

        # Verify scores
        assert "total_score" in result
        assert result["total_score"] >= 0
        assert "max_score" in result
        assert result["max_score"] > 0

        # Verify normalized score
        assert "normalized_to_20" in result
        assert 0 <= result["normalized_to_20"] <= 20

        # Verify feedback
        assert "feedback" in result
        feedback = result["feedback"]
        assert "strengths" in feedback
        assert "weaknesses" in feedback
        assert "suggestions" in feedback

        # Verify timing
        assert "duration_seconds" in result
        assert result["duration_seconds"] > 0

    def test_pipeline_with_specific_rubric(self, pipeline_config):
        """Test 2: Pipeline runs with a specific rubric version."""
        import uuid
        session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        repository_id = f"test-repo-{uuid.uuid4().hex[:8]}"

        from services.rubric_service import RubricService
        rubric_svc = RubricService()

        result = pipeline_config.evaluate_repository(
            repo_url=self.REPO_URL,
            roll_number=self.ROLL_NUMBER,
            session_id=session_id,
            repository_id=repository_id,
            rubric_version_id=rubric_svc.default_version_id,
        )

        assert result is not None
        assert result.get("pipeline_status") in ("success", "partial")

        # Verify criterion results exist
        criterion_results = result.get("criterion_results", [])
        assert len(criterion_results) > 0
        for cr in criterion_results:
            assert "criterion_key" in cr
            assert "score" in cr
            assert "confidence" in cr
