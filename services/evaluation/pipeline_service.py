"""High-level pipeline entry point integrating with the existing Flask trigger.

PipelineService wraps EvaluationOrchestrator and provides a simple interface
that can be called from existing controllers (evaluation_controller.py).
This replaces the old EvaluationService that spawned main.py as subprocess.
"""

from typing import Optional

from services.evaluation.orchestrator import EvaluationOrchestrator


class PipelineService:
    """High-level service that runs the full evaluation pipeline for repositories.

    Called from evaluation_controller.py via the existing /api/sessions/<id>/evaluate endpoint.
    """

    def __init__(self, orchestrator: Optional[EvaluationOrchestrator] = None):
        self.orchestrator = orchestrator or EvaluationOrchestrator()

    def evaluate_repository(
        self,
        repo_url: str,
        roll_number: str,
        session_id: str,
        repository_id: str,
        base_repo_url: Optional[str] = None,
        rubric_version_id: Optional[str] = None,
        force: bool = False,
    ) -> dict:
        """Evaluate a single repository through the full pipeline.

        Args:
            force: If True, clear cached step files and re-run all steps.

        Returns dict with status, scores, feedback, and any errors.
        """
        return self.orchestrator.evaluate(
            repo_url=repo_url,
            roll_number=roll_number,
            session_id=session_id,
            repository_id=repository_id,
            base_repo_url=base_repo_url,
            rubric_version_id=rubric_version_id,
            force=force,
        )

    def evaluate_session_repositories(
        self,
        session_id: str,
        repository_ids: Optional[list[str]] = None,
        rubric_version_id: Optional[str] = None,
        force: bool = False,
    ) -> list[dict]:
        """Evaluate all pending repositories in a session.

        Called from the existing evaluate_pending flow to replace old EvaluationService.

        Args:
            session_id: Session to evaluate
            repository_ids: Optional subset of repository IDs to evaluate
            rubric_version_id: Rubric version to use
            force: If True, clear cached step files and re-run all steps.

        Returns:
            list of evaluation result dicts
        """
        from services.repository_service import RepositoryService

        repo_service = RepositoryService()
        pending = repo_service.pending_repositories(session_id)

        if repository_ids:
            wanted = set(str(rid) for rid in repository_ids)
            pending = [r for r in pending if str(r["id"]) in wanted]

        if not pending:
            return []

        ids = [r["id"] for r in pending]
        repo_service.mark_running(ids)

        results = []
        errors = []

        for repo in pending:
            try:
                result = self.evaluate_repository(
                    repo_url=repo["repo_url"],
                    roll_number=repo["roll_number"],
                    session_id=session_id,
                    repository_id=str(repo["id"]),
                    rubric_version_id=rubric_version_id,
                    force=force,
                )
                results.append(result)
                repo_data = result.get("repo_data", {})
                repo_service.repository.save_analysis(
                    repo["id"],
                    repo_data,
                )
            except Exception as e:
                errors.append({"repository_id": str(repo["id"]), "error": str(e)})
                repo_service.mark_failed([repo["id"]], str(e))

        return results
