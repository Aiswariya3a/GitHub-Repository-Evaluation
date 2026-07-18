from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from services.session_service import VALID_STATUSES
from .common import services, session_context

session_controller = Blueprint("session", __name__)

@session_controller.get("/")
def dashboard(): return render_template("overview.html", title="Dashboard")

@session_controller.get("/sessions")
def sessions_page(): return render_template("dashboard.html", title="Evaluation Sessions")

@session_controller.get("/reports")
def reports_page(): return render_template("reports.html", title="Reports")

@session_controller.get("/analytics")
def analytics_page(): return render_template("analytics.html", title="Analytics")

@session_controller.get("/settings")
def settings_page(): return render_template("settings.html", title="Settings")

@session_controller.get("/sessions/<session_id>")
def detail(session_id):
    session, repositories, summary, plagiarism = session_context(session_id)
    return render_template("session.html", title=session["name"], session=session, repositories=repositories, summary=summary, plagiarism=plagiarism)

@session_controller.get("/api/sessions")
def list_api(): return jsonify(services().sessions.list_sessions())

@session_controller.post("/api/sessions")
def create_api():
    payload = request.get_json(silent=True) or {}
    try: return jsonify(services().sessions.create_session(payload.get("name", ""), payload.get("description", ""), payload.get("rubric_version_id"))), 201
    except ValueError as exc: return jsonify(error=str(exc)), 400

@session_controller.get("/api/sessions/<session_id>")
def detail_api(session_id):
    session, repositories, summary, plagiarism = session_context(session_id)
    return jsonify(session=session, repositories=repositories, summary=summary,
                   plagiarism=plagiarism, insights=services().repositories.session_insights(session_id))

@session_controller.get("/api/dashboard")
def dashboard_api():
    data = services().repositories.dashboard()
    data["pending_reviews"] = services().reviews.review_queue.total_pending()
    return jsonify(data)

@session_controller.get("/api/system/status")
def system_status_api():
    import os, platform, sys
    from datetime import datetime
    from database.postgres import connect
    stats = {}
    try:
        with connect() as db:
            rows = db.execute("""
                SELECT relname AS table_name, n_live_tup AS row_estimate
                FROM pg_stat_user_tables ORDER BY relname
            """).fetchall()
            stats["tables"] = {r["table_name"]: r["row_estimate"] for r in rows}
            exact = {}
            for tbl in ["evaluation_sessions","repositories","evaluation_results","ingestion_records","rubrics","rubric_versions","plagiarism_results"]:
                r = db.execute(f"SELECT COUNT(*) c FROM {tbl}").fetchone()
                exact[tbl] = r["c"]
            stats["table_counts"] = exact
        stats["database"] = "connected"
    except Exception as exc:
        stats["database"] = f"error: {exc}"
    ollama_config = {}
    try:
        svc = services()
        if hasattr(svc.evaluations, 'orchestrator'):
            o = svc.evaluations.orchestrator.ollama
            if o:
                ollama_config = {
                    "host": o.base_url,
                    "timeout": o.timeout,
                    "code_model": o._model_map.get("code", ""),
                    "reasoning_model": o._model_map.get("reasoning", ""),
                }
    except Exception:
        pass
    return jsonify({
        "database": stats,
        "ollama": ollama_config,
        "system": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "hostname": platform.node(),
            "server_time": datetime.now().isoformat(),
        },
        "worker": {
            "type": "pipeline (async per-repo)",
            "mode": "in_process",
        },
    })

@session_controller.patch("/api/sessions/<session_id>")
def update_api(session_id):
    payload = request.get_json(silent=True) or {}
    try:
        if not services().sessions.set_status(session_id, payload.get("status", "")): return jsonify(error="Session not found."), 404
        return jsonify(services().sessions.get_session(session_id))
    except ValueError as exc: return jsonify(error=str(exc), allowed_statuses=sorted(VALID_STATUSES)), 400

@session_controller.delete("/api/sessions/<session_id>")
def delete_api(session_id):
    return ("", 204) if services().sessions.delete_session(session_id) else (jsonify(error="Session not found."), 404)

class SessionController:
    blueprint = session_controller
