import json

from database import connect


def flatten_metadata(value, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from flatten_metadata(child, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from flatten_metadata(child, f"{prefix}[{index}]")
    else:
        yield prefix, value, "null" if value is None else type(value).__name__


class EvaluationRepository:
    def hydrate(self, row):
        evaluation = {}
        if not row or not row.get("evaluation_id"):
            return evaluation
        with connect() as db:
            questions = db.execute("SELECT * FROM evaluation_questions WHERE evaluation_id=%s ORDER BY question_code", (row["evaluation_id"],)).fetchall()
            question_data = {}
            for question in questions:
                criteria = db.execute("SELECT * FROM evaluation_criteria WHERE question_id=%s ORDER BY criterion_key", (question["id"],)).fetchall()
                question_data[question["question_code"]] = {
                    **{item["criterion_key"]: {"score": float(item["score"] or 0), "remarks": item["remarks"]} for item in criteria},
                    "total": float(question["total"] or 0),
                }
            evaluation = {"questions": question_data, "final": {
                "total_out_of_80": float(row["total_out_of_80"] or 0),
                "normalized_to_20": float(row["normalized_to_20"] or 0),
                "overall_remarks": row["overall_remarks"],
            }}
            for item in db.execute("SELECT metadata_key,metadata_value,value_type FROM evaluation_metadata WHERE evaluation_id=%s", (row["evaluation_id"],)).fetchall():
                value = item["metadata_value"]
                if item["value_type"] != "str":
                    try: value = json.loads(value)
                    except (TypeError, json.JSONDecodeError): pass
                evaluation[item["metadata_key"]] = value
        if row.get("evaluation_error"):
            return {"error": row["evaluation_error"], "details": row.get("error_details") or ""}
        return evaluation

    def save(self, repository_id, evaluation):
        final = evaluation.get("final", {}) if isinstance(evaluation, dict) else {}
        with connect() as db:
            record = db.execute("""INSERT INTO evaluations(repository_id,total_out_of_80,normalized_to_20,overall_remarks,error,error_details)
                VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(repository_id) DO UPDATE SET
                total_out_of_80=EXCLUDED.total_out_of_80,normalized_to_20=EXCLUDED.normalized_to_20,
                overall_remarks=EXCLUDED.overall_remarks,error=EXCLUDED.error,error_details=EXCLUDED.error_details,
                updated_at=now() RETURNING id""", (repository_id, final.get("total_out_of_80"),
                final.get("normalized_to_20"), final.get("overall_remarks", ""), evaluation.get("error"), evaluation.get("details"))).fetchone()
            evaluation_id = record["id"]
            db.execute("DELETE FROM evaluation_questions WHERE evaluation_id=%s", (evaluation_id,))
            db.execute("DELETE FROM evaluation_metadata WHERE evaluation_id=%s", (evaluation_id,))
            for key, value in evaluation.items():
                if key not in {"questions", "final", "error", "details"}:
                    for path, leaf, value_type in flatten_metadata(value, key):
                        db.execute("INSERT INTO evaluation_metadata(evaluation_id,metadata_key,metadata_value,value_type) VALUES (%s,%s,%s,%s)", (evaluation_id, path, None if leaf is None else str(leaf), value_type))
            for code, question in evaluation.get("questions", {}).items():
                question_id = db.execute("INSERT INTO evaluation_questions(evaluation_id,question_code,total) VALUES (%s,%s,%s) RETURNING id", (evaluation_id, code, question.get("total"))).fetchone()["id"]
                for key, value in question.items():
                    if key != "total" and isinstance(value, dict):
                        db.execute("INSERT INTO evaluation_criteria(question_id,criterion_key,score,remarks) VALUES (%s,%s,%s,%s)", (question_id, key, value.get("score"), value.get("remarks", "")))

    def save_plagiarism(self, session_id, rows):
        with connect() as db:
            for row in rows:
                db.execute("""INSERT INTO plagiarism_results(session_id,roll1,roll2,similarity) VALUES (%s,%s,%s,%s)
                    ON CONFLICT(session_id,roll1,roll2) DO UPDATE SET similarity=EXCLUDED.similarity,updated_at=now()""",
                    (session_id, row["roll1"], row["roll2"], row["similarity"]))

    def plagiarism(self, session_id):
        with connect() as db:
            return db.execute("SELECT roll1,roll2,similarity FROM plagiarism_results WHERE session_id=%s", (session_id,)).fetchall()
