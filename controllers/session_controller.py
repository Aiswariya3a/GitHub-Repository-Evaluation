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
def dashboard_api(): return jsonify(services().repositories.dashboard())

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
