"""Multi-agent SLM evaluation pipeline — agents, schemas, and orchestrator."""

from .agent_base import BaseAgent
from .schemas import (
    REPO_UNDERSTANDING_SCHEMA,
    CODE_UNDERSTANDING_SCHEMA,
    COLLABORATION_SCHEMA,
    CRITERION_EVALUATION_SCHEMA,
    FEEDBACK_SCHEMA,
)
from .ollama_router import (
    REPO_UNDERSTANDING_SYSTEM_PROMPT,
    CODE_UNDERSTANDING_SYSTEM_PROMPT,
    COLLABORATION_SYSTEM_PROMPT,
)
from .repo_understanding_agent import RepoUnderstandingAgent
from .code_understanding_agent import CodeUnderstandingAgent
from .collaboration_agent import CollaborationAgent

__all__ = [
    "BaseAgent",
    "REPO_UNDERSTANDING_SCHEMA",
    "CODE_UNDERSTANDING_SCHEMA",
    "COLLABORATION_SCHEMA",
    "CRITERION_EVALUATION_SCHEMA",
    "FEEDBACK_SCHEMA",
    "REPO_UNDERSTANDING_SYSTEM_PROMPT",
    "CODE_UNDERSTANDING_SYSTEM_PROMPT",
    "COLLABORATION_SYSTEM_PROMPT",
    "RepoUnderstandingAgent",
    "CodeUnderstandingAgent",
    "CollaborationAgent",
]
