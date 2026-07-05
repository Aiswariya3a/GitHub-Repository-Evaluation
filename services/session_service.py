from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


VALID_STATUSES = {"Active", "Completed", "Archived"}


class SessionService:
    def __init__(self, database: Path):
        self.database = database
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self):
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS evaluation_sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('Active', 'Completed', 'Archived'))
                );
                CREATE TABLE IF NOT EXISTS session_repositories (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
                    roll_number TEXT NOT NULL,
                    repo_url TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    evaluated_at TEXT,
                    repo_data TEXT,
                    evaluation_data TEXT,
                    UNIQUE(session_id, repo_url)
                );
                CREATE TABLE IF NOT EXISTS plagiarism_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES evaluation_sessions(id) ON DELETE CASCADE,
                    roll1 TEXT NOT NULL,
                    roll2 TEXT NOT NULL,
                    similarity REAL NOT NULL,
                    UNIQUE(session_id, roll1, roll2)
                );
                """
            )

    @staticmethod
    def now():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def create_session(self, name: str, description: str = ""):
        name = name.strip()
        if not name:
            raise ValueError("Session name is required.")
        session_id, now = str(uuid.uuid4()), self.now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO evaluation_sessions VALUES (?, ?, ?, ?, ?, 'Active')",
                (session_id, name, description.strip(), now, now),
            )
        return self.get_session(session_id)

    def list_sessions(self):
        with self.connect() as db:
            rows = db.execute(
                """SELECT s.*,
                    COUNT(r.id) repository_count,
                    SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) evaluated_count
                FROM evaluation_sessions s
                LEFT JOIN session_repositories r ON r.session_id = s.id
                GROUP BY s.id ORDER BY s.created_at DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, session_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM evaluation_sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None

    def set_status(self, session_id: str, status: str):
        if status not in VALID_STATUSES:
            raise ValueError("Invalid session status.")
        with self.connect() as db:
            changed = db.execute(
                "UPDATE evaluation_sessions SET status = ?, updated_at = ? WHERE id = ?",
                (status, self.now(), session_id),
            ).rowcount
        return bool(changed)

    def delete_session(self, session_id: str):
        with self.connect() as db:
            return bool(db.execute("DELETE FROM evaluation_sessions WHERE id = ?", (session_id,)).rowcount)

    def add_repositories(self, session_id: str, entries: list[dict]):
        session = self.get_session(session_id)
        if not session:
            raise LookupError("Session not found.")
        if session["status"] != "Active":
            raise ValueError("Repositories can only be added to an active session.")
        added = 0
        with self.connect() as db:
            for entry in entries:
                try:
                    db.execute(
                        """INSERT INTO session_repositories
                        (id, session_id, roll_number, repo_url, status, created_at)
                        VALUES (?, ?, ?, ?, 'Pending', ?)""",
                        (str(uuid.uuid4()), session_id, entry["roll"], entry["repo"], self.now()),
                    )
                    added += 1
                except sqlite3.IntegrityError:
                    continue
            db.execute("UPDATE evaluation_sessions SET updated_at = ? WHERE id = ?", (self.now(), session_id))
        return added

    def repositories(self, session_id: str):
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM session_repositories WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["repo_data"] = json.loads(item["repo_data"]) if item["repo_data"] else {}
            item["evaluation_data"] = json.loads(item["evaluation_data"]) if item["evaluation_data"] else {}
            result.append(item)
        return result

    def pending_repositories(self, session_id: str):
        return [repo for repo in self.repositories(session_id) if repo["status"] in {"Pending", "Failed"}]

    def recover_interrupted_evaluations(self):
        """Return work abandoned by a stopped/reloaded web process to the queue."""
        with self.connect() as db:
            return db.execute(
                """UPDATE session_repositories
                SET status = 'Pending', error = 'Previous evaluation was interrupted; ready to retry.'
                WHERE status = 'Evaluating'"""
            ).rowcount

    def mark_running(self, repository_ids: list[str]):
        if not repository_ids:
            return
        placeholders = ",".join("?" for _ in repository_ids)
        with self.connect() as db:
            db.execute(f"UPDATE session_repositories SET status = 'Evaluating', error = '' WHERE id IN ({placeholders})", repository_ids)

    def save_results(self, session_id: str, repo_rows: list[dict], evaluation_rows: list[dict], plagiarism_rows: list[dict]):
        repo_by_roll = {str(row.get("roll_number", "")).strip(): row for row in repo_rows}
        eval_by_roll = {str(row.get("roll_number", "")).strip(): row for row in evaluation_rows}
        now = self.now()
        with self.connect() as db:
            running = db.execute(
                "SELECT id, roll_number FROM session_repositories WHERE session_id = ? AND status = 'Evaluating'",
                (session_id,),
            ).fetchall()
            for item in running:
                roll = item["roll_number"]
                repo_data, evaluation_data = repo_by_roll.get(roll), eval_by_roll.get(roll)
                if repo_data is None and evaluation_data is None:
                    db.execute("UPDATE session_repositories SET status = 'Failed', error = ? WHERE id = ?", ("Evaluator produced no result.", item["id"]))
                else:
                    db.execute(
                        """UPDATE session_repositories SET status = 'Completed', evaluated_at = ?,
                        repo_data = ?, evaluation_data = ?, error = '' WHERE id = ?""",
                        (now, json.dumps(repo_data or {}), json.dumps(evaluation_data or {}), item["id"]),
                    )
            for row in plagiarism_rows:
                db.execute(
                    """INSERT OR REPLACE INTO plagiarism_results
                    (session_id, roll1, roll2, similarity) VALUES (?, ?, ?, ?)""",
                    (session_id, str(row.get("roll1", "")), str(row.get("roll2", "")), float(row.get("similarity", 0) or 0)),
                )
            db.execute("UPDATE evaluation_sessions SET updated_at = ? WHERE id = ?", (now, session_id))

    def mark_failed(self, repository_ids: list[str], error: str):
        if not repository_ids:
            return
        placeholders = ",".join("?" for _ in repository_ids)
        with self.connect() as db:
            db.execute(f"UPDATE session_repositories SET status = 'Failed', error = ? WHERE id IN ({placeholders})", [error, *repository_ids])

    def plagiarism(self, session_id: str):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT roll1, roll2, similarity FROM plagiarism_results WHERE session_id = ?", (session_id,)).fetchall()]
