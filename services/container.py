from dataclasses import dataclass
from pathlib import Path

from .evaluation_service import EvaluationService
from .report_service import ReportService
from .repository_service import RepositoryService
from .session_service import SessionService


@dataclass
class ServiceContainer:
    sessions: SessionService
    repositories: RepositoryService
    evaluations: EvaluationService
    reports: ReportService

    @classmethod
    def build(cls, root: Path):
        sessions = SessionService()
        repositories = RepositoryService()
        repositories.recover_interrupted_evaluations()
        return cls(sessions, repositories, EvaluationService(root, repositories), ReportService(root, repositories))
