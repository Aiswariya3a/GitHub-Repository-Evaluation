from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_file, url_for

from services.evaluation_service import EvaluationService
from services.report_service import ReportService
from services.session_service import SessionService, VALID_STATUSES


ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.secret_key = "repo-eval-workflow"
sessions = SessionService(ROOT / "data" / "evaluation_sessions.db")
sessions.recover_interrupted_evaluations()
evaluator = EvaluationService(ROOT, sessions)
reports = ReportService(ROOT, sessions)


def parse_repo_input(urls_text: str, rolls_text: str):
    urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    rolls = [line.strip() for line in rolls_text.splitlines() if line.strip()]
    rolls += [f"student-{index + 1}" for index in range(len(rolls), len(urls))]
    return [{"roll": rolls[index], "repo": url} for index, url in enumerate(urls)]


def parse_evaluation(payload):
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, json.JSONDecodeError):
            payload = {}
    final = (payload or {}).get("final", {}) or {}
    total = float(final.get("total_out_of_80", 0) or 0)
    normalized = float(final.get("normalized_to_20", total / 4) or 0)
    if normalized >= 16:
        label = "Strong"
    elif normalized >= 12:
        label = "On track"
    elif normalized >= 8:
        label = "Needs review"
    else:
        label = "Needs attention"
    return total, round(normalized, 2), str(final.get("overall_remarks", "Evaluation completed.")), label


def as_bool(value):
    return value is True or str(value).strip().lower() in {"true", "1", "yes"}


def session_context(session_id):
    session = sessions.get_session(session_id)
    if not session:
        abort(404)
    rows = []
    for repository in sessions.repositories(session_id):
        repo_data, evaluation_row = repository["repo_data"], repository["evaluation_data"]
        evaluation = evaluation_row.get("evaluation", {}) if evaluation_row else {}
        total, normalized, remarks, label = parse_evaluation(evaluation)
        status = repository["status"]
        is_public = as_bool(repo_data.get("public", False))
        has_readme = as_bool(repo_data.get("readme_exists", False))
        if status == "Completed":
            if not is_public:
                label = "Blocked"
            elif not has_readme:
                label = "Missing README"
            status = label
        rows.append({**repository, "repo": repository["repo_url"], "score": total, "normalized": normalized,
                     "remarks": remarks, "display_status": status, "commit_count": repo_data.get("commit_count", 0),
                     "public": is_public, "readme": has_readme,
                     "progress": 100 if repository["status"] == "Completed" else (50 if repository["status"] == "Evaluating" else 8)})
    completed = [row for row in rows if row["status"] == "Completed"]
    average = sum(row["normalized"] for row in completed) / len(completed) if completed else 0
    return session, rows, {
        "total": len(rows), "completed": len(completed), "pending": sum(row["status"] in {"Pending", "Failed"} for row in rows),
        "average": round(average, 1), "public": sum(row["public"] for row in completed),
        "readme": sum(row["readme"] for row in completed),
    }


@app.get("/")
def dashboard():
    all_sessions = sessions.list_sessions()
    return render_template("dashboard.html", title="Evaluation Sessions", sessions=all_sessions,
                           active_count=sum(item["status"] == "Active" for item in all_sessions),
                           completed_count=sum(item["status"] == "Completed" for item in all_sessions))


@app.post("/sessions")
def create_session():
    try:
        session = sessions.create_session(request.form.get("name", ""), request.form.get("description", ""))
        flash("Evaluation session created.")
        return redirect(url_for("view_session", session_id=session["id"]))
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("dashboard"))


@app.get("/sessions/<session_id>")
def view_session(session_id):
    session, repositories, summary = session_context(session_id)
    return render_template("session.html", title=session["name"], session=session, repositories=repositories, summary=summary)


@app.post("/sessions/<session_id>/repositories")
def add_repositories(session_id):
    entries = parse_repo_input(request.form.get("repo_urls", ""), request.form.get("roll_numbers", ""))
    if not entries:
        flash("Add at least one repository URL.")
    else:
        try:
            added = sessions.add_repositories(session_id, entries)
            flash(f"Added {added} repositories. Duplicates were left unchanged.")
        except (LookupError, ValueError) as exc:
            flash(str(exc))
    return redirect(url_for("view_session", session_id=session_id))


@app.post("/sessions/<session_id>/evaluate")
def evaluate_session(session_id):
    session = sessions.get_session(session_id)
    if not session:
        abort(404)
    if session["status"] != "Active":
        flash("Only active sessions can run evaluations.")
    else:
        try:
            count = evaluator.evaluate_pending(session_id)
            flash(f"Evaluation completed for {count} repositories." if count else "All repositories already have saved evaluations.")
        except Exception as exc:
            flash(f"Evaluation failed: {exc}")
    return redirect(url_for("view_session", session_id=session_id))


@app.post("/sessions/<session_id>/status")
def update_session_status(session_id):
    status = request.form.get("status", "")
    try:
        sessions.set_status(session_id, status)
        flash(f"Session marked {status.lower()}.")
    except ValueError as exc:
        flash(str(exc))
    return redirect(url_for("view_session", session_id=session_id))


@app.post("/sessions/<session_id>/delete")
def delete_session(session_id):
    sessions.delete_session(session_id)
    flash("Session deleted.")
    return redirect(url_for("dashboard"))


@app.get("/sessions/<session_id>/report")
def download_report(session_id):
    if not sessions.get_session(session_id):
        abort(404)
    try:
        temp, path = reports.generate(session_id)
        response = send_file(path, as_attachment=True, download_name=f"session-{session_id}-report.pdf")
        response.call_on_close(temp.cleanup)
        return response
    except Exception as exc:
        flash(str(exc))
        return redirect(url_for("view_session", session_id=session_id))


# JSON APIs mirror the browser workflow for integrations and progress polling.
@app.get("/api/sessions")
def api_sessions():
    return jsonify(sessions.list_sessions())


@app.post("/api/sessions")
def api_create_session():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(sessions.create_session(payload.get("name", ""), payload.get("description", ""))), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.get("/api/sessions/<session_id>")
def api_session(session_id):
    session, repositories, summary = session_context(session_id)
    return jsonify(session=session, repositories=repositories, summary=summary)


@app.patch("/api/sessions/<session_id>")
def api_update_session(session_id):
    payload = request.get_json(silent=True) or {}
    try:
        if not sessions.set_status(session_id, payload.get("status", "")):
            return jsonify(error="Session not found."), 404
        return jsonify(sessions.get_session(session_id))
    except ValueError as exc:
        return jsonify(error=str(exc), allowed_statuses=sorted(VALID_STATUSES)), 400


@app.post("/api/sessions/<session_id>/repositories")
def api_add_repositories(session_id):
    payload = request.get_json(silent=True) or {}
    entries = payload.get("repositories", [])
    normalized = [{"repo": str(item.get("repo_url", "")).strip(),
                   "roll": str(item.get("roll_number") or f"student-{index + 1}").strip()}
                  for index, item in enumerate(entries) if str(item.get("repo_url", "")).strip()]
    try:
        return jsonify(added=sessions.add_repositories(session_id, normalized)), 201
    except LookupError as exc:
        return jsonify(error=str(exc)), 404
    except ValueError as exc:
        return jsonify(error=str(exc)), 409


@app.post("/api/sessions/<session_id>/evaluate")
def api_evaluate_session(session_id):
    session = sessions.get_session(session_id)
    if not session:
        return jsonify(error="Session not found."), 404
    if session["status"] != "Active":
        return jsonify(error="Only active sessions can run evaluations."), 409
    try:
        return jsonify(evaluated=evaluator.evaluate_pending(session_id))
    except Exception as exc:
        return jsonify(error=str(exc)), 500


@app.delete("/api/sessions/<session_id>")
def api_delete_session(session_id):
    return ("", 204) if sessions.delete_session(session_id) else (jsonify(error="Session not found."), 404)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
