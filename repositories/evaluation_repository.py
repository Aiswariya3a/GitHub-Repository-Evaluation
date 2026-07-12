from typing import Optional

from psycopg.types.json import Jsonb

from database import connect

class EvaluationRepository:
    def save_plagiarism(self, session_id, rows):
        with connect() as db:
            for row in rows:
                db.execute("""INSERT INTO plagiarism_results(session_id,roll1,roll2,similarity) VALUES (%s,%s,%s,%s)
                    ON CONFLICT(session_id,roll1,roll2) DO UPDATE SET similarity=EXCLUDED.similarity,updated_at=now()""",
                    (session_id, row["roll1"], row["roll2"], row["similarity"]))

    def plagiarism(self, session_id):
        with connect() as db:
            return db.execute("SELECT roll1,roll2,similarity FROM plagiarism_results WHERE session_id=%s", (session_id,)).fetchall()

    def save_evaluation_result(self, repository_id: str, session_id: str,
                               rubric_version_id: str, result: dict) -> str:
        """Save or update pipeline evaluation result for a repository.

        Args:
            result: dict with keys:
                - repo_understanding, code_understanding, collaboration (capability JSONs)
                - total_score, max_score, normalized_to_20, percentage
                - criterion_results (list of criterion dicts)
                - low_confidence_criteria (list of strings)
                - feedback (Feedback Agent output dict)
                - pipeline_status: 'success', 'partial', or 'failed'
                - failed_agents: list of agent names that failed
                - error: optional error message
        """
        with connect() as db:
            row = db.execute("""
                INSERT INTO evaluation_results (
                    repository_id, session_id, rubric_version_id,
                    repo_understanding, code_understanding, collaboration,
                    total_score, max_score, normalized_to_20, percentage,
                    criterion_results, low_confidence_criteria,
                    feedback, pipeline_status, failed_agents, error,
                    evaluation_started_at, evaluation_completed_at
                ) VALUES (%s,%s,%s, %s,%s,%s, %s,%s,%s,%s, %s,%s, %s,%s,%s,%s,
                    CASE WHEN %s::text IS NOT NULL THEN %s::timestamptz ELSE NOW() END,
                    NOW()
                ) ON CONFLICT (repository_id, session_id) DO UPDATE SET
                    repo_understanding=EXCLUDED.repo_understanding,
                    code_understanding=EXCLUDED.code_understanding,
                    collaboration=EXCLUDED.collaboration,
                    total_score=EXCLUDED.total_score,
                    max_score=EXCLUDED.max_score,
                    normalized_to_20=EXCLUDED.normalized_to_20,
                    percentage=EXCLUDED.percentage,
                    criterion_results=EXCLUDED.criterion_results,
                    low_confidence_criteria=EXCLUDED.low_confidence_criteria,
                    feedback=EXCLUDED.feedback,
                    pipeline_status=EXCLUDED.pipeline_status,
                    failed_agents=EXCLUDED.failed_agents,
                    error=EXCLUDED.error,
                    evaluation_completed_at=NOW(),
                    updated_at=NOW()
                RETURNING id
            """, (
                repository_id, session_id, rubric_version_id,
                Jsonb(result.get("repo_understanding")),
                Jsonb(result.get("code_understanding")),
                Jsonb(result.get("collaboration")),
                result.get("total_score", 0),
                result.get("max_score", 0),
                result.get("normalized_to_20", 0),
                result.get("percentage", 0),
                Jsonb(result.get("criterion_results", [])),
                Jsonb(result.get("low_confidence_criteria", [])),
                Jsonb(result.get("feedback")),
                result.get("pipeline_status", "success"),
                Jsonb(result.get("failed_agents", [])),
                result.get("error"),
                result.get("evaluation_started_at"),
                result.get("evaluation_started_at"),
            ))
            return str(row["id"])

    def get_evaluation_result(self, repository_id: str, session_id: str) -> Optional[dict]:
        with connect() as db:
            return db.execute("""
                SELECT * FROM evaluation_results
                WHERE repository_id=%s AND session_id=%s
            """, (repository_id, session_id)).fetchone()
