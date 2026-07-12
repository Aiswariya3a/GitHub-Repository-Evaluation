from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class EvaluationSession:
    id: UUID
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    rubric_version_id: UUID


@dataclass(frozen=True)
class Repository:
    id: UUID
    session_id: UUID
    roll_number: str
    repo_url: str
    evaluation_status: str
    created_at: datetime
    updated_at: datetime

