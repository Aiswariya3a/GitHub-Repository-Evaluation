from dataclasses import dataclass
from pathlib import Path

from .evaluation_service import EvaluationService
from .report_service import ReportService
from .repository_service import RepositoryService
from .session_service import SessionService
from .rubric_service import RubricService


@dataclass
class ServiceContainer:
    sessions: SessionService
    repositories: RepositoryService
    evaluations: EvaluationService
    reports: ReportService
    rubrics: RubricService

    @classmethod
    def build(cls, root: Path):
        rubrics=RubricService()
        sessions = SessionService(default_rubric_version_id=rubrics.default_version_id)
        repositories = RepositoryService()
        repositories.recover_interrupted_evaluations()
        return cls(sessions, repositories, EvaluationService(root, repositories), ReportService(root, repositories), rubrics)
