from flask import Blueprint, jsonify, request

from .common import services
from services.rubric_service import RubricService

review_controller = Blueprint("review", __name__)


@review_controller.get("/api/reviews/<session_id>")
def list_queue(session_id):
    status = request.args.get("status")
    queue = services().reviews.list_queue(session_id, status)
    pending = services().reviews.pending_count(session_id)
    return jsonify(queue=queue, total=len(queue), pending=pending)


@review_controller.get("/api/reviews/<session_id>/<repository_id>")
def review_detail(session_id, repository_id):
    svc = services().reviews
    entry = svc.get_queue_entry(repository_id, session_id)
    evaluation = None
    try:
        from repositories import EvaluationRepository
        evaluation = EvaluationRepository().get_evaluation_result(repository_id, session_id)
    except Exception:
        pass
    overrides = svc.get_overrides(repository_id, session_id)
    audit = svc.get_audit_trail(repository_id, session_id)
    rubric = None
    if evaluation and evaluation.get("rubric_version_id"):
        try:
            rubric = RubricService().get_version(evaluation["rubric_version_id"])
        except Exception:
            pass
    return jsonify(queue=entry, evaluation=evaluation, overrides=overrides, audit=audit, rubric=rubric)


@review_controller.post("/api/reviews/<session_id>/<repository_id>/start")
def start_review(session_id, repository_id):
    svc = services().reviews
    entry = svc.get_queue_entry(repository_id, session_id)
    if not entry:
        return jsonify(error="Repository not found in review queue."), 404
    if entry.get("status") != "pending":
        return jsonify(error="Review cannot be started from current status."), 409
    svc.start_review(repository_id, session_id)
    return jsonify(status="in_review")


@review_controller.post("/api/reviews/<session_id>/<repository_id>/override")
def submit_override(session_id, repository_id):
    body = request.get_json(silent=True) or {}
    criterion_key = body.get("criterion_key", "")
    overridden_score = body.get("overridden_score")
    reasoning = body.get("reasoning", "")
    performed_by = body.get("performed_by", "instructor")
    if overridden_score is None:
        return jsonify(error="overridden_score is required."), 400
    try:
        record = services().reviews.override_score(
            repository_id, session_id, criterion_key,
            float(overridden_score), reasoning, performed_by,
        )
        return jsonify(record)
    except Exception as exc:
        return jsonify(error=str(exc)), 500


@review_controller.post("/api/reviews/<session_id>/<repository_id>/complete")
def complete_review(session_id, repository_id):
    svc = services().reviews
    entry = svc.get_queue_entry(repository_id, session_id)
    if not entry:
        return jsonify(error="Repository not found in review queue."), 404
    svc.complete_review(repository_id, session_id)
    return jsonify(status="reviewed")


@review_controller.get("/api/reviews/<session_id>/<repository_id>/audit")
def audit_trail(session_id, repository_id):
    audit = services().reviews.get_audit_trail(repository_id, session_id)
    return jsonify(audit=audit)


class ReviewController:
    blueprint = review_controller
