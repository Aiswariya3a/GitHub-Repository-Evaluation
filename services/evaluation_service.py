from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pandas as pd

from .session_service import SessionService


_evaluation_lock = threading.Lock()
OUTPUTS = ("repo_report.csv", "evaluation_report.csv", "plagiarism_report.csv")


class EvaluationService:
    """Adapts the unchanged file-based evaluator to durable session storage."""

    def __init__(self, root: Path, sessions: SessionService):
        self.root, self.sessions = root, sessions

    @staticmethod
    def read_records(path: Path):
        if not path.exists() or not path.stat().st_size:
            return []
        # Round-tripping through pandas JSON converts numpy scalars into values
        # that can be stored safely in the session database.
        import json
        try:
            frame = pd.read_csv(path).fillna("")
        except pd.errors.EmptyDataError:
            # An empty plagiarism report is a valid "no matches" result.
            return []
        return json.loads(frame.to_json(orient="records"))

    def evaluate_pending(self, session_id: str):
        pending = self.sessions.pending_repositories(session_id)
        if not pending:
            return 0
        ids = [repo["id"] for repo in pending]
        self.sessions.mark_running(ids)
        with _evaluation_lock:
            try:
                # main.py intentionally remains unchanged and file-based. Run it
                # in a disposable workspace so OneDrive, open CSV previews, and
                # concurrent web requests cannot lock the application's files.
                with tempfile.TemporaryDirectory(prefix="repository-evaluation-") as workspace:
                    run_directory = Path(workspace)
                    pd.DataFrame(
                        [{"roll_number": repo["roll_number"], "repo_url": repo["repo_url"]} for repo in pending]
                    ).to_csv(run_directory / "repos.csv", index=False)
                    print(
                        f"[session {session_id}] Starting main.py for {len(pending)} repository/repositories...",
                        flush=True,
                    )
                    completed = subprocess.run(
                        [sys.executable, "-u", str(self.root / "main.py")],
                        cwd=run_directory,
                        timeout=1800,
                    )
                    if completed.returncode:
                        raise RuntimeError(f"Evaluator exited with status {completed.returncode}. See the Flask terminal for details.")
                    self.sessions.save_results(
                        session_id,
                        self.read_records(run_directory / "repo_report.csv"),
                        self.read_records(run_directory / "evaluation_report.csv"),
                        self.read_records(run_directory / "plagiarism_report.csv"),
                    )
                    print(f"[session {session_id}] Evaluation completed and results were saved.", flush=True)
            except Exception as exc:
                self.sessions.mark_failed(ids, str(exc))
                raise
        return len(pending)
