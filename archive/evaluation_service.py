# Archived in Phase 3 — replaced by PipelineService
from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .repository_service import RepositoryService


_evaluation_lock = threading.Lock()
class EvaluationService:
    """Runs the evaluator while PostgreSQL remains its durable input/output."""

    def __init__(self, root: Path, repositories: RepositoryService, runner=None):
        self.root, self.repositories = root, repositories
        self.runner = runner or subprocess.run

    def evaluate_pending(self, session_id: str, repository_ids=None):
        pending = self.repositories.pending_repositories(session_id)
        if repository_ids is not None:
            wanted = {str(item) for item in repository_ids}
            pending = [repo for repo in pending if str(repo["id"]) in wanted]
        if not pending:
            return 0
        ids = [repo["id"] for repo in pending]
        self.repositories.mark_running(ids)
        with _evaluation_lock:
            try:
                # Clone data remains disposable; all durable input and output is
                # read from and written to PostgreSQL by main.py.
                with tempfile.TemporaryDirectory(prefix="repository-evaluation-") as workspace:
                    run_directory = Path(workspace)
                    print(
                        f"[session {session_id}] Starting main.py for {len(pending)} repository/repositories...",
                        flush=True,
                    )
                    completed = self.runner(
                        [sys.executable, "-u", str(self.root / "main.py"), "--session-id", str(session_id)],
                        cwd=run_directory,
                        timeout=1800,
                    )
                    if completed.returncode:
                        raise RuntimeError(f"Evaluator exited with status {completed.returncode}. See the Flask terminal for details.")
                    print(f"[session {session_id}] Evaluation completed and results were saved.", flush=True)
            except Exception as exc:
                self.repositories.mark_failed(ids, str(exc))
                raise
        return len(pending)
