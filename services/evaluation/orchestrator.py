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
import shutil
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
from dataclasses import asdict, is_dataclass
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
            "ingestion": self._step_output_path(session_dir, "ingestion"),
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

    def _attach_evidence_keys(self, feedback: dict, criterion_results: list[dict]) -> None:
        """Populate evidence_keys programmatically from criterion results.

        Matches each strength/weakness area text against criterion metadata
        (criterion_key, name, name_without_prefix, category_code) using
        case-insensitive substring matching. This eliminates LLM hallucination
        of evidence_keys (T-02-04).
        """
        if not isinstance(feedback, dict):
            return
        # Build search texts for each criterion
        criteria_index: list[tuple[str, str]] = []
        for cr in criterion_results:
            ck = str(cr.get("criterion_key", "") or "")
            name = str(cr.get("criterion_name", "") or "")
            cat = str(cr.get("category_code", "") or "")
            criteria_index.append((ck, f"{cat}/{ck} {name} {ck.replace('_', ' ')} {name.lower()}"))

        for section in ("strengths", "weaknesses"):
            items = feedback.get(section)
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                area = str(item.get("area", "") or "").lower()
                matched = []
                for ck, search_text in criteria_index:
                    if area and area in search_text.lower():
                        matched.append(ck)
                item["evidence_keys"] = matched if matched else []

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
        """Run independent agents in parallel respecting max_parallel (ORC-04)."""
        print(f"[DIAG] _run_parallel_agents: launching {len(agents)} agents (max_workers={self.max_parallel})")
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
        force: bool = False,
    ) -> dict:
        """Run the full evaluation pipeline for a single repository.

        Args:
            repo_url: GitHub repository URL
            roll_number: Student roll number
            session_id: Evaluation session ID
            repository_id: Repository record ID
            base_repo_url: Optional base repository URL for delta
            rubric_version_id: Rubric version to evaluate against
            force: If True, clear cached step files and re-run all steps

        Returns:
            dict: Full pipeline result with all agent outputs, scores, feedback
        """
        start_time = time.monotonic()
        session_dir = self._create_session_dir(session_id, repository_id)
        print(f"[DIAG] Evaluate called: force={force}, session_dir={session_dir}")
        if force and os.path.exists(session_dir):
            shutil.rmtree(session_dir)
            os.makedirs(session_dir, exist_ok=True)
            logger.info(f"Force re-evaluation: cleared cache at {session_dir}")
            print(f"[DIAG] Cache cleared at {session_dir}")
        completed = self._detect_completed_steps(session_dir)
        print(f"[DIAG] Completed steps after detection: {list(completed.keys())}")

        # --- Step 1: Ingestion ---
        if "ingestion" not in completed:
            logger.info("Step 1: Running ingestion")
            print(f"[DIAG] Step 1: Ingestion will run (ingestion not in completed)")
            ingestion_result = self.ingestion_service.ingest(
                repo_url=repo_url,
                roll_number=roll_number,
                base_repo_url=base_repo_url,
                repository_id=repository_id,
            )
            print(f"[DIAG] Ingestion returned: status={ingestion_result.get('status')}, "
                  f"has_snapshot={'snapshot' in ingestion_result}, "
                  f"has_rec_id={bool(ingestion_result.get('ingestion_record_id'))}, "
                  f"error={ingestion_result.get('error')}")
            snapshot = ingestion_result.get("snapshot")
            if not snapshot:
                # Try loading from ingestion_repo
                rec_id = ingestion_result.get("ingestion_record_id")
                if rec_id:
                    record = self.ingestion_repo.get_ingestion_by_id(str(rec_id))
                    snapshot = record["snapshot"] if record else None
            if not snapshot:
                print(f"[DIAG] SNAPSHOT IS NONE. Returning early with failed status")
                return {
                    "status": "failed",
                    "error": "Ingestion produced no snapshot",
                    "failed_agents": [],
                    "results": {},
                }
            print(f"[DIAG] Snapshot OK: {len(snapshot.get('files', []))} files, "
                  f"repo_stats keys={list(snapshot.get('repo_stats', {}).keys())}")
            # Cache snapshot
            snapshot_path = self._step_output_path(session_dir, "ingestion")
            with open(snapshot_path, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
            print(f"[DIAG] Ingestion complete: snapshot saved ({len(snapshot.get('files', []))} files in snapshot)")
        else:
            snapshot = completed["ingestion"]

        # --- Step 2: Capability Extraction (parallel) ---
        if all(s in completed for s in ["repo_understanding", "code_understanding", "collaboration"]):
            logger.info("Step 2: All capability outputs found, skipping")
            print("[DIAG] Step 2: All capability outputs found, skipping")
            repo_out = completed["repo_understanding"]
            code_out = completed["code_understanding"]
            collab_out = completed["collaboration"]
        else:
            logger.info("Step 2: Running capability extraction agents")
            print("[DIAG] Step 2: Running capability extraction agents (this will call Ollama)")
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
            print("[DIAG] Step 3: Criteria found, skipping")
            criterion_results = completed["criteria"]
        else:
            logger.info("Step 3: Running rubric criteria evaluation")
            print("[DIAG] Step 3: Running criteria evaluation")
            rubric_version_id = rubric_version_id or self.rubric_service.default_version_id
            rubric = self.rubric_service.get_version(rubric_version_id)

            all_criteria = []
            for cat in rubric["categories"]:
                all_criteria.extend([(cat, crit) for crit in cat["criteria"]])

            criterion_results = []
            criteria_agents = []

            for cat, crit in all_criteria:
                try:
                    evidence = route_evidence(snapshot, cat["code"], criterion_key=crit["criterion_key"])
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
                except Exception as e:
                    logger.error(
                        "Failed to setup criterion %s/%s: %s",
                        cat["code"], crit["criterion_key"], e,
                    )

            crit_results = self._run_parallel_agents(criteria_agents, session_dir)
            criterion_results = [v for v in crit_results.values() if v is not None]

            # Log returned keys for debugging (key mismatch detection)
            expected = {(cat["code"], crit["criterion_key"]) for cat, crit in all_criteria}
            returned = {(cr.get("category_code", ""), cr.get("criterion_key", "")) for cr in criterion_results}
            logger.info(
                "Criteria evaluation: %d/%d returned (expected %d keys, got %d matches)",
                len(criterion_results),
                len(all_criteria),
                len(expected),
                len(expected & returned),
            )
            missing = expected - returned
            if missing:
                logger.warning("Criteria keys missing from results: %s", sorted(missing))
            extra = returned - expected
            if extra:
                logger.warning("Criteria keys NOT in rubric: %s", sorted(extra))

            # Cache combined criteria
            criteria_path = self._step_output_path(session_dir, "criteria")
            with open(criteria_path, "w") as f:
                json.dump(criterion_results, f, indent=2, default=str)

        # --- Step 4: Score Aggregation (deterministic) ---
        if "aggregation" in completed:
            logger.info("Step 4: Aggregation output found, skipping")
            print("[DIAG] Step 4: Aggregation found, skipping")
            aggregated = completed["aggregation"]
        else:
            logger.info("Step 4: Aggregating scores")
            print("[DIAG] Step 4: Aggregating scores")
            rubric = self.rubric_service.get_version(rubric_version_id)
            aggregated = aggregate_scores(criterion_results, rubric)
            agg_path = self._step_output_path(session_dir, "aggregation")
            with open(agg_path, "w") as f:
                agg_dict = asdict(aggregated) if is_dataclass(aggregated) else aggregated
                json.dump(agg_dict, f, indent=2)

        # --- Step 5: Feedback Generation (sequential) ---
        if "feedback" in completed:
            logger.info("Step 5: Feedback output found, skipping")
            print("[DIAG] Step 5: Feedback found, skipping")
            feedback = completed["feedback"]
        else:
            logger.info("Step 5: Generating feedback")
            print("[DIAG] Step 5: Generating feedback")
            feedback_input = {
                "aggregated_result": asdict(aggregated) if is_dataclass(aggregated) else aggregated,
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

        # Post-process feedback: attach evidence_keys programmatically using
        # criterion results instead of relying on LLM output (T-02-04).
        self._attach_evidence_keys(feedback, criterion_results)

        # --- Step 6: Persist to PostgreSQL (ORC-07) ---
        pipeline_status = "success"
        if self.failed_agents:
            pipeline_status = "partial"

        agg_dict = asdict(aggregated) if is_dataclass(aggregated) else (aggregated or {})

        snapshot_meta = snapshot if isinstance(snapshot, dict) else {}
        if "github_metadata" not in snapshot_meta:
            try:
                cached = self._step_output_path(session_dir, "ingestion")
                if os.path.exists(cached):
                    with open(cached) as f:
                        snapshot_meta = json.load(f)
            except Exception:
                pass
        repo_meta = snapshot_meta.get("github_metadata", {})
        eval_result = {
            "repo_data": {
                "public": repo_meta.get("is_public", False),
                "readme_exists": repo_meta.get("readme_exists", False),
                "commit_count": repo_meta.get("commits_count", 0),
            },
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
        print(f"[DIAG] evaluate() returning: status={pipeline_status}, duration={round(duration, 1)}s")

        return eval_result
