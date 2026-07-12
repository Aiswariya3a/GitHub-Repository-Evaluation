from dataclasses import dataclass
from pathlib import Path

from .evaluation.pipeline_service import PipelineService
from .report_service import ReportService
from .repository_service import RepositoryService
from .session_service import SessionService
from .rubric_service import RubricService


@dataclass
class ServiceContainer:
    sessions: SessionService
    repositories: RepositoryService
    evaluations: PipelineService
    reports: ReportService
    rubrics: RubricService

    @classmethod
    def build(cls, root: Path):
        rubrics=RubricService()
        sessions = SessionService(default_rubric_version_id=rubrics.default_version_id)
        repositories = RepositoryService()
        repositories.recover_interrupted_evaluations()
        try:
            pipeline = PipelineService()
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize PipelineService: {exc}") from exc
        return cls(sessions, repositories, pipeline, ReportService(root, repositories), rubrics)
