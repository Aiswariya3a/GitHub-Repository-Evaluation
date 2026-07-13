from flask import Blueprint, jsonify

from .common import services

evaluation_controller = Blueprint("evaluation", __name__)

def validate_session(session_id):
    session = services().sessions.get_session(session_id)
    if not session: return None, (jsonify(error="Session not found."), 404)
    if session["status"] != "Active": return None, (jsonify(error="Only active sessions can run evaluations."), 409)
    return session, None

def _session_rubric_version_id(session):
    if not session:
        return None
    return session.get("rubric_version_id")

@evaluation_controller.post("/api/sessions/<session_id>/evaluate")
def evaluate_session(session_id):
    session, error = validate_session(session_id)
    if error: return error
    try:
        results = services().evaluations.evaluate_session_repositories(
            session_id, rubric_version_id=_session_rubric_version_id(session),
        )
        return jsonify(evaluated=len(results), results=results)
    except Exception as exc: return jsonify(error=str(exc)), 500

@evaluation_controller.post("/api/sessions/<session_id>/repositories/<repository_id>/evaluate")
def evaluate_repository(session_id, repository_id):
    session, error = validate_session(session_id)
    if error: return error
    repository = services().repositories.get_repository(session_id, repository_id)
    if not repository: return jsonify(error="Repository not found."), 404
    if repository["status"] == "Completed": return jsonify(error="Use the re-evaluate endpoint for a completed repository."), 409
    services().repositories.queue_repository(session_id, repository_id)
    try:
        results = services().evaluations.evaluate_session_repositories(
            session_id, [repository_id], rubric_version_id=_session_rubric_version_id(session),
        )
        return jsonify(evaluated=len(results), results=results)
    except Exception as exc: return jsonify(error=str(exc)), 500

@evaluation_controller.post("/api/sessions/<session_id>/repositories/<repository_id>/reevaluate")
def reevaluate_repository(session_id, repository_id):
    session, error = validate_session(session_id)
    if error: return error
    if not services().repositories.queue_repository(session_id, repository_id): return jsonify(error="Repository not found."), 404
    try:
        results = services().evaluations.evaluate_session_repositories(
            session_id, [repository_id], rubric_version_id=_session_rubric_version_id(session), force=True,
        )
        return jsonify(evaluated=len(results), results=results)
    except Exception as exc: return jsonify(error=str(exc)), 500

class EvaluationController:
    blueprint = evaluation_controller
