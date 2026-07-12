"""Multi-agent pipeline orchestrator (ORC-01).

Manages the full evaluation pipeline lifecycle:
1. Load snapshot (ingestion JSON)
2. Run capability agents in parallel (AGN-04)
3. Run rubric criteria evaluation in parallel (EVA-04)
4. Aggregate scores deterministically (EVA-06)
5. Generate feedback (FDB-01/02)
6. Persist to PostgreSQL (ORC-07)
"""

import json
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

from services.evaluation.repo_understanding_agent import RepoUnderstandingAgent
from services.evaluation.code_understanding_agent import CodeUnderstandingAgent
from services.evaluation.collaboration_agent import CollaborationAgent
from services.evaluation.rubric_evaluation_agent import RubricEvaluationAgent, RUBRIC_EVALUATION_SYSTEM_PROMPT
from services.evaluation.feedback_agent import FeedbackAgent, FEEDBACK_SYSTEM_PROMPT
from services.evaluation.schemas import (
    REPO_UNDERSTANDING_SCHEMA,
    CODE_UNDERSTANDING_SCHEMA,
    COLLABORATION_SCHEMA,
    CRITERION_EVALUATION_SCHEMA,
    FEEDBACK_SCHEMA,
)
from services.evaluation.score_aggregator import aggregate_scores
from services.evaluation.evidence_router import route_evidence
from services.ingestion_service import IngestionService
from services.rubric_service import RubricService
from repositories.ingestion_repository import IngestionRepository
from repositories.evaluation_repository import EvaluationRepository
from services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class EvaluationOrchestrator:
    """Manages the multi-agent evaluation pipeline lifecycle."""

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        ingestion_service: Optional[IngestionService] = None,
        rubric_service: Optional[RubricService] = None,
        evaluation_repo: Optional[EvaluationRepository] = None,
        ingestion_repo: Optional[IngestionRepository] = None,
        working_dir: Optional[str] = None,
        max_parallel_agents: int = 2,  # D-08, D-10
        max_retries: int = 2,          # ORC-03
        execution_mode: str = "in_process",  # D-02
    ):
        self.ollama = ollama_client or OllamaClient()
        self.ingestion_service = ingestion_service or IngestionService()
        self.rubric_service = rubric_service or RubricService()
        self.evaluation_repo = evaluation_repo or EvaluationRepository()
        self.ingestion_repo = ingestion_repo or IngestionRepository()
        self.base_working_dir = working_dir or os.getcwd()
        self.max_parallel = max_parallel_agents
        self.max_retries = max_retries
        self.execution_mode = execution_mode

        # Agent instances
        self.repo_agent = RepoUnderstandingAgent(self.ollama, execution_mode)
        self.code_agent = CodeUnderstandingAgent(self.ollama, execution_mode)
        self.collab_agent = CollaborationAgent(self.ollama, execution_mode)
        self.rubric_agent = RubricEvaluationAgent(self.ollama, execution_mode)
        self.feedback_agent = FeedbackAgent(self.ollama, execution_mode)

        # Step status tracking
        self.failed_agents: list[str] = []

    def _create_session_dir(self, session_id: str, repository_id: str) -> str:
        """Create per-session working directory (ORC-06)."""
        session_dir = os.path.join(
            self.base_working_dir, "evaluations", session_id, repository_id
        )
        os.makedirs(session_dir, exist_ok=True)
        return session_dir

    def _step_output_path(self, session_dir: str, step: str) -> str:
        """Get expected output file path for a pipeline step (D-11, D-12)."""
        return os.path.join(session_dir, f"{step}.json")

    def _detect_completed_steps(self, session_dir: str) -> dict:
        """Check which step outputs already exist (idempotent recovery per D-11, D-12).

        Returns dict of {step_name: output_dict} for completed steps.
        """
        completed = {}
        step_files = {
            "repo_understanding": self._step_output_path(session_dir, "repo_understanding"),
            "code_understanding": self._step_output_path(session_dir, "code_understanding"),
            "collaboration": self._step_output_path(session_dir, "collaboration"),
            "criteria": self._step_output_path(session_dir, "criteria"),
            "aggregation": self._step_output_path(session_dir, "aggregation"),
            "feedback": self._step_output_path(session_dir, "feedback"),
        }
        for step, path in step_files.items():
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        completed[step] = json.load(f)
                    logger.info(f"Recovery: {step} output found at {path}, skipping")
                except (json.JSONDecodeError, IOError):
                    logger.warning(f"Recovery: {step} output corrupted at {path}, will re-run")
        return completed

    def _run_agent_with_retry(self, agent, agent_name: str, input_data: dict,
                               output_path: str, schema: dict, step_name: str) -> Optional[dict]:
        """Run an agent with retry logic (ORC-03).

        Returns agent output dict on success, None on failure after retries.
        """
        for attempt in range(1 + self.max_retries):
            try:
                logger.info(f"Running {agent_name} (attempt {attempt + 1})")
                result = agent.run(input_data, output_path)

                valid, errors = agent._validate_output(result, schema)
                if valid:
                    return result
                else:
                    logger.warning(f"{agent_name} attempt {attempt + 1}: schema validation failed: {errors}")
            except Exception as e:
                logger.error(f"{agent_name} attempt {attempt + 1}: error: {e}")

        self.failed_agents.append(agent_name)
        return None

    def _run_parallel_agents(self, agents: list[tuple], session_dir: str) -> dict:
        """Run independent agents in parallel respecting max_parallel (ORC-04).

        Args:
            agents: list of tuples (agent_callable, agent_name, step_name)
        Returns:
            dict: {step_name: output_dict or None}
        """
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            future_map = {}
            for agent_fn, agent_name, step_name in agents:
                future = executor.submit(agent_fn)
                future_map[future] = (agent_name, step_name)

            for future in as_completed(future_map):
                agent_name, step_name = future_map[future]
                try:
                    results[step_name] = future.result()
                    logger.info(f"Completed: {agent_name}")
                except Exception as e:
                    logger.error(f"Failed: {agent_name}: {e}")
                    self.failed_agents.append(agent_name)
                    results[step_name] = None
        return results

    def evaluate(
        self,
        repo_url: str,
        roll_number: str,
        session_id: str,
        repository_id: str,
        base_repo_url: Optional[str] = None,
        rubric_version_id: Optional[str] = None,
    ) -> dict:
        """Run the full evaluation pipeline for a single repository.

        Args:
            repo_url: GitHub repository URL
            roll_number: Student roll number
            session_id: Evaluation session ID
            repository_id: Repository record ID
            base_repo_url: Optional base repository URL for delta
            rubric_version_id: Rubric version to evaluate against

        Returns:
            dict: Full pipeline result with all agent outputs, scores, feedback
        """
        start_time = time.monotonic()
        session_dir = self._create_session_dir(session_id, repository_id)
        completed = self._detect_completed_steps(session_dir)

        # --- Step 1: Ingestion ---
        if "repo_understanding" not in completed:
            logger.info("Step 1: Running ingestion")
            ingestion_result = self.ingestion_service.ingest(
                repo_url=repo_url,
                roll_number=roll_number,
                base_repo_url=base_repo_url,
                repository_id=repository_id,
            )
            snapshot = ingestion_result.get("snapshot")
            if not snapshot:
                # Try loading from ingestion_repo
                rec_id = ingestion_result.get("ingestion_record_id")
                if rec_id:
                    record = self.ingestion_repo.get_ingestion_by_id(str(rec_id))
                    snapshot = record["snapshot"] if record else None
            if not snapshot:
                return {
                    "status": "failed",
                    "error": "Ingestion produced no snapshot",
                    "failed_agents": [],
                    "results": {},
                }
            # Cache snapshot path
            snapshot_path = self._step_output_path(session_dir, "ingestion")
            with open(snapshot_path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
        else:
            snapshot = completed["repo_understanding"]

        # --- Step 2: Capability Extraction (parallel) ---
        if all(s in completed for s in ["repo_understanding", "code_understanding", "collaboration"]):
            logger.info("Step 2: All capability outputs found, skipping")
            repo_out = completed["repo_understanding"]
            code_out = completed["code_understanding"]
            collab_out = completed["collaboration"]
        else:
            logger.info("Step 2: Running capability extraction agents")
            agents = [
                (lambda: self._run_agent_with_retry(
                    self.repo_agent, "RepoUnderstandingAgent", snapshot,
                    self._step_output_path(session_dir, "repo_understanding"),
                    REPO_UNDERSTANDING_SCHEMA, "repo_understanding"),
                 "RepoUnderstandingAgent", "repo_understanding"),
                (lambda: self._run_agent_with_retry(
                    self.code_agent, "CodeUnderstandingAgent", snapshot,
                    self._step_output_path(session_dir, "code_understanding"),
                    CODE_UNDERSTANDING_SCHEMA, "code_understanding"),
                 "CodeUnderstandingAgent", "code_understanding"),
                (lambda: self._run_agent_with_retry(
                    self.collab_agent, "CollaborationAgent", snapshot,
                    self._step_output_path(session_dir, "collaboration"),
                    COLLABORATION_SCHEMA, "collaboration"),
                 "CollaborationAgent", "collaboration"),
            ]
            cap_results = self._run_parallel_agents(agents, session_dir)
            repo_out = cap_results.get("repo_understanding")
            code_out = cap_results.get("code_understanding")
            collab_out = cap_results.get("collaboration")

        # --- Step 3: Rubric Evaluation (parallel per criterion) ---
        if "criteria" in completed:
            logger.info("Step 3: Criteria evaluation output found, skipping")
            criterion_results = completed["criteria"]
        else:
            logger.info("Step 3: Running rubric criteria evaluation")
            rubric_version_id = rubric_version_id or self.rubric_service.default_version_id
            rubric = self.rubric_service.get_version(rubric_version_id)

            all_criteria = []
            for cat in rubric["categories"]:
                all_criteria.extend([(cat, crit) for crit in cat["criteria"]])

            criterion_results = []
            criteria_agents = []

            for cat, crit in all_criteria:
                evidence = route_evidence(snapshot, cat["code"])
                input_data = {
                    "criterion_key": crit["criterion_key"],
                    "category_code": cat["code"],
                    "criterion_name": crit["name"],
                    "max_score": float(crit["max_score"]),
                    "evidence": evidence,
                }
                output_path = self._step_output_path(
                    session_dir, f"criterion_{cat['code']}_{crit['criterion_key']}"
                )

                # Create closure to capture variables
                def make_agent_fn(agent, inp, out_path, schema, name):
                    return lambda: self._run_agent_with_retry(
                        agent, name, inp, out_path, schema, name
                    )

                agent_name = f"RubricEval_{cat['code']}.{crit['criterion_key']}"
                criteria_agents.append((
                    make_agent_fn(self.rubric_agent, input_data, output_path,
                                  CRITERION_EVALUATION_SCHEMA,
                                  agent_name),
                    agent_name,
                    f"criterion_{cat['code']}_{crit['criterion_key']}",
                ))

            crit_results = self._run_parallel_agents(criteria_agents, session_dir)
            criterion_results = [v for v in crit_results.values() if v is not None]

            # Cache combined criteria
            criteria_path = self._step_output_path(session_dir, "criteria")
            with open(criteria_path, "w") as f:
                json.dump(criterion_results, f, indent=2, default=str)

        # --- Step 4: Score Aggregation (deterministic) ---
        if "aggregation" in completed:
            logger.info("Step 4: Aggregation output found, skipping")
            aggregated = completed["aggregation"]
        else:
            logger.info("Step 4: Aggregating scores")
            rubric = self.rubric_service.get_version(rubric_version_id)
            aggregated = aggregate_scores(criterion_results, rubric)
            agg_path = self._step_output_path(session_dir, "aggregation")
            with open(agg_path, "w") as f:
                # AggregatedScore dataclass -> dict
                if hasattr(aggregated, '__dict__'):
                    agg_dict = {k: v for k, v in aggregated.__dict__.items()
                                if not k.startswith('_')}
                else:
                    agg_dict = aggregated
                json.dump(agg_dict, f, indent=2, default=str)

        # --- Step 5: Feedback Generation (sequential) ---
        if "feedback" in completed:
            logger.info("Step 5: Feedback output found, skipping")
            feedback = completed["feedback"]
        else:
            logger.info("Step 5: Generating feedback")
            feedback_input = {
                "aggregated_result": aggregated.__dict__ if hasattr(aggregated, '__dict__') else aggregated,
                "criterion_results": criterion_results,
                "low_confidence_criteria": (
                    aggregated.low_confidence_criteria
                    if hasattr(aggregated, 'low_confidence_criteria')
                    else []
                ),
            }
            feedback_result = self._run_agent_with_retry(
                self.feedback_agent, "FeedbackAgent",
                feedback_input,
                self._step_output_path(session_dir, "feedback"),
                FEEDBACK_SCHEMA, "feedback",
            )
            feedback = feedback_result if feedback_result else {
                "strengths": [], "weaknesses": [], "suggestions": [],
                "summary": "Feedback generation failed",
            }

        # --- Step 6: Persist to PostgreSQL (ORC-07) ---
        pipeline_status = "success"
        if self.failed_agents:
            pipeline_status = "partial"

        # Convert AggregatedScore to dict if needed
        agg_dict = aggregated
        if hasattr(aggregated, '__dict__'):
            agg_dict = {k: v for k, v in aggregated.__dict__.items()
                        if not k.startswith('_')}
            if "categories" in agg_dict and hasattr(agg_dict["categories"], '__iter__'):
                agg_dict["categories"] = [
                    {k: v for k, v in cat.__dict__.items() if not k.startswith('_')}
                    if hasattr(cat, '__dict__') else cat
                    for cat in agg_dict["categories"]
                ]

        eval_result = {
            "repo_understanding": repo_out,
            "code_understanding": code_out,
            "collaboration": collab_out,
            "total_score": agg_dict.get("total_score", 0),
            "max_score": agg_dict.get("max_score", 0),
            "normalized_to_20": agg_dict.get("normalized_to_20", 0),
            "percentage": agg_dict.get("percentage", 0),
            "criterion_results": criterion_results,
            "low_confidence_criteria": agg_dict.get("low_confidence_criteria", []),
            "feedback": feedback,
            "pipeline_status": pipeline_status,
            "failed_agents": self.failed_agents,
            "error": None if pipeline_status == "success" else f"Failed agents: {self.failed_agents}",
            "evaluation_started_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self.evaluation_repo.save_evaluation_result(
                repository_id=repository_id,
                session_id=session_id,
                rubric_version_id=rubric_version_id or self.rubric_service.default_version_id,
                result=eval_result,
            )
        except Exception as e:
            logger.error(f"Failed to persist results to PostgreSQL: {e}")
            eval_result["persistence_error"] = str(e)

        duration = time.monotonic() - start_time
        eval_result["duration_seconds"] = round(duration, 1)

        return eval_result
