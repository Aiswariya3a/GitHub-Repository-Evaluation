from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from .session_service import SessionService


class ReportService:
    def __init__(self, root: Path, sessions: SessionService):
        self.root, self.sessions = root, sessions

    def generate(self, session_id: str):
        repositories = [repo for repo in self.sessions.repositories(session_id) if repo["status"] == "Completed"]
        if not repositories:
            raise ValueError("This session has no saved evaluations to report.")
        temp = tempfile.TemporaryDirectory(prefix="evaluation-report-")
        directory = Path(temp.name)
        pd.DataFrame([repo["repo_data"] for repo in repositories]).to_csv(directory / "repo_report.csv", index=False)
        pd.DataFrame([repo["evaluation_data"] for repo in repositories]).to_csv(directory / "evaluation_report.csv", index=False)
        pd.DataFrame(self.sessions.plagiarism(session_id), columns=["roll1", "roll2", "similarity"]).to_csv(directory / "plagiarism_report.csv", index=False)
        completed = subprocess.run([sys.executable, str(self.root / "pdf_gen.py")], cwd=directory, capture_output=True, text=True, timeout=1800)
        if completed.returncode or not (directory / "Final_Consolidated_Report.pdf").exists():
            temp.cleanup()
            raise RuntimeError(completed.stderr.strip() or "PDF generation failed.")
        return temp, directory / "Final_Consolidated_Report.pdf"
