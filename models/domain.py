from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class EvaluationSession:
    id: UUID
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Repository:
    id: UUID
    session_id: UUID
    roll_number: str
    repo_url: str
    evaluation_status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Evaluation:
    id: UUID
    repository_id: UUID
    total_out_of_80: Decimal | None
    normalized_to_20: Decimal | None
    overall_remarks: str
    created_at: datetime
    updated_at: datetime
