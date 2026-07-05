from flask import Blueprint, jsonify

from .common import services

evaluation_controller = Blueprint("evaluation", __name__)

def validate_session(session_id):
    session = services().sessions.get_session(session_id)
    if not session: return None, (jsonify(error="Session not found."), 404)
    if session["status"] != "Active": return None, (jsonify(error="Only active sessions can run evaluations."), 409)
    return session, None

@evaluation_controller.post("/api/sessions/<session_id>/evaluate")
def evaluate_session(session_id):
    _, error = validate_session(session_id)
    if error: return error
    try: return jsonify(evaluated=services().evaluations.evaluate_pending(session_id))
    except Exception as exc: return jsonify(error=str(exc)), 500

@evaluation_controller.post("/api/sessions/<session_id>/repositories/<repository_id>/evaluate")
def evaluate_repository(session_id, repository_id):
    _, error = validate_session(session_id)
    if error: return error
    repository = services().repositories.get_repository(session_id, repository_id)
    if not repository: return jsonify(error="Repository not found."), 404
    if repository["status"] == "Completed": return jsonify(error="Use the re-evaluate endpoint for a completed repository."), 409
    services().repositories.queue_repository(session_id, repository_id)
    try: return jsonify(evaluated=services().evaluations.evaluate_pending(session_id, [repository_id]))
    except Exception as exc: return jsonify(error=str(exc)), 500

@evaluation_controller.post("/api/sessions/<session_id>/repositories/<repository_id>/reevaluate")
def reevaluate_repository(session_id, repository_id):
    _, error = validate_session(session_id)
    if error: return error
    if not services().repositories.queue_repository(session_id, repository_id): return jsonify(error="Repository not found."), 404
    try: return jsonify(evaluated=services().evaluations.evaluate_pending(session_id, [repository_id]))
    except Exception as exc: return jsonify(error=str(exc)), 500

class EvaluationController:
    blueprint = evaluation_controller
