"""One-time migration of the previous SQLite session store into PostgreSQL."""
from __future__ import annotations

import json
import sqlite3
import sys
import csv
import uuid
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database import connect, initialize_database
from services.session_service import SessionService
from services.repository_service import RepositoryService


SOURCE = ROOT / "data" / "evaluation_sessions.db"


def decode(value):
    if not value:
        return {}
    return json.loads(value)


def csv_rows(name):
    path = ROOT / name
    if not path.exists() or not path.stat().st_size:
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def migrate_legacy_reports(repositories):
    repo_rows = csv_rows("repo_report.csv")
    evaluation_rows = csv_rows("evaluation_report.csv")
    plagiarism_rows = csv_rows("plagiarism_report.csv")
    if not repo_rows and not evaluation_rows:
        return
    session_id = uuid.uuid5(uuid.NAMESPACE_URL, "repository-evaluation:legacy-reports")
    with connect() as db:
        db.execute(
            """INSERT INTO evaluation_sessions(id,name,description,status)
            VALUES (%s,'Imported legacy reports','Imported from the former global CSV persistence.','Completed')
            ON CONFLICT(id) DO NOTHING""", (session_id,)
        )
    repo_by_roll = {str(row.get("roll_number", "")).strip(): row for row in repo_rows}
    eval_by_roll = {str(row.get("roll_number", "")).strip(): row for row in evaluation_rows}
    for roll in sorted(set(repo_by_roll) | set(eval_by_roll)):
        repo_row, eval_row = repo_by_roll.get(roll, {}), eval_by_roll.get(roll, {})
        repo_url = repo_row.get("repo") or eval_row.get("repo") or f"legacy://{roll}"
        repository_id = uuid.uuid5(session_id, repo_url)
        with connect() as db:
            db.execute(
                """INSERT INTO repositories(id,session_id,roll_number,repo_url,evaluation_status)
                VALUES (%s,%s,%s,%s,'Pending') ON CONFLICT(id) DO NOTHING""",
                (repository_id, session_id, roll, repo_url),
            )
        evaluation = decode(eval_row.get("evaluation")) if eval_row else {}
        repositories.save_repository_evaluation(repository_id, {
            "public": as_bool(repo_row.get("public")),
            "readme_exists": as_bool(repo_row.get("readme_exists")),
            "commit_count": int(float(repo_row.get("commit_count") or 0)),
        }, evaluation)
    repositories.save_plagiarism(session_id, [{
        "roll1": row.get("roll1", ""), "roll2": row.get("roll2", ""),
        "similarity": float(row.get("similarity") or 0),
    } for row in plagiarism_rows])


def main():
    load_dotenv(ROOT / ".env")
    initialize_database()
    SessionService()
    repositories = RepositoryService()
    if SOURCE.exists():
        source = sqlite3.connect(SOURCE)
        source.row_factory = sqlite3.Row
        with connect() as target:
            for session in source.execute("SELECT * FROM evaluation_sessions"):
                target.execute(
                    """INSERT INTO evaluation_sessions(id,name,description,status,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING""",
                    (session["id"], session["name"], session["description"], session["status"], session["created_at"], session["updated_at"]),
                )
            for repository in source.execute("SELECT * FROM session_repositories"):
                repo_data, evaluation_row = decode(repository["repo_data"]), decode(repository["evaluation_data"])
                target.execute(
                    """INSERT INTO repositories(id,session_id,roll_number,repo_url,evaluation_status,error,
                    is_public,readme_exists,commit_count,evaluated_at,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING""",
                    (repository["id"], repository["session_id"], repository["roll_number"], repository["repo_url"],
                     repository["status"], repository["error"], repo_data.get("public"), repo_data.get("readme_exists"),
                     repo_data.get("commit_count"), repository["evaluated_at"], repository["created_at"], repository["created_at"]),
                )
                target.commit()
                if evaluation_row:
                    evaluation = evaluation_row.get("evaluation", evaluation_row)
                    if isinstance(evaluation, str):
                        evaluation = json.loads(evaluation)
                    repositories.save_repository_evaluation(repository["id"], repo_data, evaluation)
            for item in source.execute("SELECT roll1,roll2,similarity,session_id FROM plagiarism_results"):
                repositories.save_plagiarism(item["session_id"], [dict(item)])
        source.close()
    migrate_legacy_reports(repositories)
    print("Legacy session data migrated to PostgreSQL.")


if __name__ == "__main__":
    main()
