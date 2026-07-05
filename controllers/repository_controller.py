from flask import Blueprint, jsonify, request

from .common import services

repository_controller = Blueprint("repository", __name__)

@repository_controller.post("/api/sessions/<session_id>/repositories")
def add_api(session_id):
    items = (request.get_json(silent=True) or {}).get("repositories", [])
    entries = [{"repo": str(item.get("repo_url", "")).strip(), "roll": str(item.get("roll_number") or f"student-{index+1}").strip()} for index,item in enumerate(items) if str(item.get("repo_url", "")).strip()]
    try: return jsonify(added=services().repositories.add_repositories(session_id, entries)), 201
    except LookupError as exc: return jsonify(error=str(exc)), 404
    except ValueError as exc: return jsonify(error=str(exc)), 409

class RepositoryController:
    blueprint = repository_controller
