from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from .repository_service import RepositoryService


class ReportService:
    def __init__(self, root: Path, repositories: RepositoryService):
        self.root, self.repositories = root, repositories

    def generate(self, session_id: str):
        repositories = [repo for repo in self.repositories.list_repositories(session_id) if repo["status"] == "Completed"]
        if not repositories:
            raise ValueError("This session has no saved evaluations to report.")
        temp = tempfile.TemporaryDirectory(prefix="evaluation-report-")
        directory = Path(temp.name)
        completed = subprocess.run(
            [sys.executable, str(self.root / "pdf_gen.py"), "--session-id", str(session_id)],
            cwd=directory, capture_output=True, text=True, timeout=1800,
        )
        if completed.returncode or not (directory / "Final_Consolidated_Report.pdf").exists():
            temp.cleanup()
            raise RuntimeError(completed.stderr.strip() or "PDF generation failed.")
        return temp, directory / "Final_Consolidated_Report.pdf"

    def generate_repository(self, session_id: str, repository_id: str):
        repository = self.repositories.get_repository(session_id, repository_id)
        if not repository or repository["status"] != "Completed":
            raise ValueError("This repository has no saved evaluation to report.")
        temp, _ = self.generate(session_id)
        report = Path(temp.name) / "student_reports" / f"{repository['roll_number'].strip().upper()}.pdf"
        if not report.exists():
            temp.cleanup()
            raise RuntimeError("Repository report generation failed.")
        return temp, report
