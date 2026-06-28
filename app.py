from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, flash, redirect, render_template, request, send_file, url_for

app = Flask(__name__)
app.secret_key = "repo-eval-workflow"
ROOT = Path(__file__).resolve().parent


def read_csv_if_available(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def parse_evaluation(payload: object) -> dict[str, object]:
    if payload is None or pd.isna(payload):
        return {
            "score": 0,
            "normalized": 0.0,
            "remarks": "No evaluation available yet.",
            "status": "Pending",
        }

    try:
        data = payload if isinstance(payload, dict) else json.loads(str(payload))
    except Exception:
        return {
            "score": 0,
            "normalized": 0.0,
            "remarks": "Evaluation payload could not be parsed.",
            "status": "Pending",
        }

    final = data.get("final", {}) or {}
    total = float(final.get("total_out_of_80", 0) or 0)
    normalized = float(final.get("normalized_to_20", round(total / 4, 2)) or 0)
    remarks = str(final.get("overall_remarks", "Evaluation completed."))

    if normalized >= 16:
        status = "Strong"
    elif normalized >= 12:
        status = "On track"
    elif normalized >= 8:
        status = "Needs review"
    else:
        status = "Needs attention"

    return {
        "score": int(total),
        "normalized": round(normalized, 2),
        "remarks": remarks,
        "status": status,
    }


def build_dashboard_context() -> tuple[list[dict], list[dict], list[dict], dict]:
    repo_df = read_csv_if_available(ROOT / "repo_report.csv")
    evaluation_df = read_csv_if_available(ROOT / "evaluation_report.csv")
    plagiarism_df = read_csv_if_available(ROOT / "plagiarism_report.csv")

    if not repo_df.empty:
        repo_df = repo_df.copy()
        repo_df.columns = [str(c).strip() for c in repo_df.columns]

    if not evaluation_df.empty:
        evaluation_df = evaluation_df.copy()
        evaluation_df.columns = [str(c).strip() for c in evaluation_df.columns]

    repo_rows: list[dict] = []
    for _, row in repo_df.iterrows():
        roll = str(row.get("roll_number", "")).strip()
        repo_url = str(row.get("repo", "")).strip() or "Repository unavailable"
        public = bool(row.get("public", False)) if not pd.isna(row.get("public", False)) else False
        readme = bool(row.get("readme_exists", False)) if not pd.isna(row.get("readme_exists", False)) else False
        commit_count = int(row.get("commit_count", 0)) if not pd.isna(row.get("commit_count", 0)) else 0

        evaluation_row = None
        if not evaluation_df.empty:
            by_roll = evaluation_df[evaluation_df["roll_number"].astype(str).str.strip() == roll] if "roll_number" in evaluation_df.columns else pd.DataFrame()
            if by_roll.empty and "repo" in evaluation_df.columns:
                by_roll = evaluation_df[evaluation_df["repo"].astype(str).str.strip() == repo_url]
            if not by_roll.empty:
                evaluation_row = by_roll.iloc[0]

        evaluation = parse_evaluation(evaluation_row.get("evaluation") if evaluation_row is not None else None)

        if not public:
            status = "Blocked"
        elif not readme:
            status = "Missing README"
        else:
            status = str(evaluation["status"])

        repo_rows.append(
            {
                "roll_number": roll,
                "repo": repo_url,
                "public": public,
                "readme": readme,
                "commit_count": commit_count,
                "score": int(evaluation["score"]),
                "normalized": float(evaluation["normalized"]),
                "remarks": str(evaluation["remarks"]),
                "status": status,
                "progress": min(100, max(8, int(float(evaluation["normalized"]) / 20 * 100))),
            }
        )

    repo_rows = sorted(repo_rows, key=lambda item: item["normalized"], reverse=True)
    total_repos = len(repo_rows)
    ready_count = sum(1 for item in repo_rows if item["status"] in {"Strong", "On track"})
    public_count = sum(1 for item in repo_rows if item["public"])
    readme_count = sum(1 for item in repo_rows if item["readme"])
    average_score = round(sum(item["normalized"] for item in repo_rows) / total_repos, 2) if total_repos else 0.0
    average_commits = round(sum(item["commit_count"] for item in repo_rows) / total_repos, 1) if total_repos else 0.0
    plagiarism_count = len(plagiarism_df) if not plagiarism_df.empty else 0

    metrics = [
        {"label": "Total repositories", "value": total_repos, "tone": "indigo"},
        {"label": "Ready to review", "value": ready_count, "tone": "emerald"},
        {"label": "Avg. score", "value": f"{average_score:.1f}/20", "tone": "amber"},
        {"label": "Plagiarism flags", "value": plagiarism_count, "tone": "red"},
    ]

    return repo_rows, metrics, [item for item in repo_rows if item["status"] in {"Needs attention", "Missing README", "Blocked"}], {
        "public_count": public_count,
        "readme_count": readme_count,
        "average_commits": average_commits,
        "top_repos": repo_rows[:4],
    }


def parse_repo_input(urls_text: str, rolls_text: str) -> list[dict]:
    urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    rolls = [line.strip() for line in rolls_text.splitlines() if line.strip()]

    if not urls:
        return []

    if not rolls:
        rolls = [f"student-{index + 1}" for index in range(len(urls))]
    elif len(rolls) < len(urls):
        rolls.extend([f"student-{index + 1}" for index in range(len(rolls), len(urls))])
    elif len(rolls) > len(urls):
        rolls = rolls[: len(urls)]

    return [{"roll": roll, "repo": url} for roll, url in zip(rolls, urls)]


def run_evaluation(entries: list[dict]) -> tuple[bool, str]:
    if not entries:
        return False, "Add at least one repository URL before running the evaluation."

    backup = None
    repos_path = ROOT / "repos.csv"
    if repos_path.exists():
        backup = repos_path.read_text(encoding="utf-8")

    try:
        pd.DataFrame(
            [{"roll_number": entry["roll"], "repo_url": entry["repo"]} for entry in entries]
        ).to_csv(repos_path, index=False)

        completed = subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=1800,
        )

        if completed.returncode != 0:
            return False, completed.stderr.strip() or completed.stdout.strip() or "The evaluator did not complete successfully."

        return True, "Evaluation completed."
    except subprocess.TimeoutExpired:
        return False, "The evaluation timed out. Try a smaller batch or check your API configuration."
    except Exception as exc:
        return False, f"Evaluation failed: {exc}"
    finally:
        if backup is None:
            repos_path.unlink(missing_ok=True)
        else:
            repos_path.write_text(backup, encoding="utf-8")


@app.route("/download-pdf")
def download_pdf():
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "pdf_gen.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=1800,
        )

        if completed.returncode != 0:
            flash(completed.stderr.strip() or completed.stdout.strip() or "PDF generation failed.")
            return redirect(url_for("index"))

        pdf_path = ROOT / "Final_Consolidated_Report.pdf"
        if not pdf_path.exists():
            flash("The consolidated PDF report was not generated.")
            return redirect(url_for("index"))

        return send_file(pdf_path, as_attachment=True, download_name="Final_Consolidated_Report.pdf")
    except subprocess.TimeoutExpired:
        flash("PDF generation timed out. Please try again.")
        return redirect(url_for("index"))
    except Exception as exc:
        flash(f"PDF generation failed: {exc}")
        return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    repo_rows, metrics, needs_attention, summary = build_dashboard_context()
    message = None

    if request.method == "POST":
        entries = parse_repo_input(request.form.get("repo_urls", ""), request.form.get("roll_numbers", ""))
        if not entries:
            flash("Add at least one repository URL to start an evaluation.")
        else:
            success, message = run_evaluation(entries)
            if success:
                flash("Evaluation completed. Review the latest results below.")
            else:
                flash(message)

        repo_rows, metrics, needs_attention, summary = build_dashboard_context()

    return render_template(
        "index.html",
        title="Repository Evaluation Studio",
        subtitle="Paste GitHub links, run the evaluation workflow, and inspect the scored results in one place.",
        metrics=metrics,
        repo_rows=repo_rows,
        needs_attention=needs_attention,
        summary=summary,
        message=message,
        repo_urls=request.form.get("repo_urls", "") if request.method == "POST" else "",
        roll_numbers=request.form.get("roll_numbers", "") if request.method == "POST" else "",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
