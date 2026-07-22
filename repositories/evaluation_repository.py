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
            )).fetchone()
            return str(row["id"])

    def hydrate(self, row):
        if not row.get("evaluation_id"):
            return None
        return {
            "id": row["evaluation_id"],
            "total_out_of_80": row.get("total_score") or 0,
            "total_score": row.get("total_score") or 0,
            "max_score": row.get("max_score") or 0,
            "normalized_to_20": row.get("normalized_to_20") or 0,
            "rubric_version_id": row.get("evaluation_rubric_version_id"),
            "overall_remarks": row.get("overall_remarks") or "",
            "error": row.get("evaluation_error"),
            "error_details": row.get("error_details"),
        }

    def get_evaluation_result(self, repository_id: str, session_id: str) -> Optional[dict]:
        with connect() as db:
            return db.execute("""
                SELECT * FROM evaluation_results
                WHERE repository_id=%s AND session_id=%s
            """, (repository_id, session_id)).fetchone()

    def apply_override(self, repository_id: str, session_id: str,
                       criterion_key: str, new_score: float) -> dict:
        with connect() as db:
            row = db.execute("""
                SELECT criterion_results, max_score FROM evaluation_results
                WHERE repository_id=%s AND session_id=%s
            """, (repository_id, session_id)).fetchone()
            if not row:
                return {}
            criteria = list(row["criterion_results"] or [])
            max_total = float(row.get("max_score") or 80)
            parts = criterion_key.split(".", 1)
            cat_code, crit_key = parts[0] if len(parts) > 1 else "", parts[-1] if len(parts) > 1 else criterion_key
            updated = False
            for cr in criteria:
                ck = cr.get("criterion_key", "")
                cc = cr.get("category_code", "")
                if ck == crit_key and (not cat_code or cc == cat_code):
                    cr["score"] = new_score
                    cr["overridden"] = True
                    updated = True
                    break
            if not updated:
                for cr in criteria:
                    ck = cr.get("criterion_key", "") or cr.get("key", "")
                    if ck == criterion_key:
                        cr["score"] = new_score
                        cr["overridden"] = True
                        updated = True
                        break
            total = sum(float(cr.get("score", 0)) for cr in criteria)
            normalized = round((total / max_total) * 20, 2) if max_total > 0 else 0
            db.execute("""
                UPDATE evaluation_results SET
                    criterion_results=%s,
                    total_score=%s,
                    normalized_to_20=%s,
                    percentage=%s,
                    updated_at=now()
                WHERE repository_id=%s AND session_id=%s
            """, (Jsonb(criteria), total, normalized, round((total / max_total) * 100, 2) if max_total > 0 else 0,
                  repository_id, session_id))
            return {"total_score": total, "normalized_to_20": normalized, "max_score": max_total}
