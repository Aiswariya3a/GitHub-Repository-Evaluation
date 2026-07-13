from __future__ import annotations
import tempfile
from pathlib import Path

from .repository_service import RepositoryService


class ReportService:
    def __init__(self, root: Path, repositories: RepositoryService):
        self.root, self.repositories = root, repositories

    def generate(self, session_id: str):
        from pdf_gen import generate_pdf
        temp = tempfile.TemporaryDirectory(prefix="evaluation-report-")
        directory = Path(temp.name)
        try:
            report_path = generate_pdf(session_id, str(directory))
            return temp, report_path
        except Exception as exc:
            temp.cleanup()
            raise RuntimeError(f"PDF generation failed: {exc}") from exc

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
