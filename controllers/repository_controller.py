from flask import Blueprint, abort, jsonify, render_template, request

from .common import services

repository_controller = Blueprint("repository", __name__)

@repository_controller.get("/api/search")
def search_api():
    query = request.args.get("q", "").strip()
    return jsonify(results=services().repositories.search(query))

@repository_controller.get("/sessions/<session_id>/repositories/<repository_id>")
def detail(session_id, repository_id):
    repository = services().repositories.get_repository(session_id, repository_id)
    if not repository: abort(404)
    return render_template("repository_detail.html", title=repository["roll_number"], session_id=session_id, repository_id=repository_id)

@repository_controller.get("/api/sessions/<session_id>/repositories/<repository_id>")
def detail_api(session_id, repository_id):
    repository = services().repositories.repository_detail(session_id, repository_id)
    return jsonify(repository=repository) if repository else (jsonify(error="Repository not found."), 404)

@repository_controller.post("/api/sessions/<session_id>/repositories")
def add_api(session_id):
    items = (request.get_json(silent=True) or {}).get("repositories", [])
    entries = [{"repo": str(item.get("repo_url", "")).strip(), "roll": str(item.get("roll_number") or f"student-{index+1}").strip()} for index,item in enumerate(items) if str(item.get("repo_url", "")).strip()]
    try: return jsonify(added=services().repositories.add_repositories(session_id, entries)), 201
    except LookupError as exc: return jsonify(error=str(exc)), 404
    except ValueError as exc: return jsonify(error=str(exc)), 409

class RepositoryController:
    blueprint = repository_controller
