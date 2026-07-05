from flask import Blueprint, abort, jsonify, render_template, request

from .common import services

rubric_controller=Blueprint("rubric",__name__)

@rubric_controller.get("/rubrics")
def index():return render_template("rubrics.html",title="Rubrics")

@rubric_controller.get("/rubrics/new")
def create_page():return render_template("rubric_new.html",title="Create rubric")

@rubric_controller.get("/rubrics/<version_id>")
def detail(version_id):
    if not services().rubrics.get_version(version_id):abort(404)
    return render_template("rubric_detail.html",title="Rubric detail",version_id=version_id)

@rubric_controller.get("/api/rubrics")
def list_api():return jsonify(services().rubrics.list_rubrics(request.args.get("archived")=="true"))

@rubric_controller.get("/api/rubrics/versions/<version_id>")
def version_api(version_id):
    rubric=services().rubrics.get_version(version_id)
    return jsonify(rubric=rubric) if rubric else (jsonify(error="Rubric not found."),404)

@rubric_controller.post("/api/rubrics")
def create_api():
    payload=request.get_json(silent=True) or {}
    try:return jsonify(services().rubrics.create(payload.get("name",""),payload.get("description",""),payload.get("categories",[]))),201
    except ValueError as exc:return jsonify(error=str(exc)),400

@rubric_controller.post("/api/rubrics/versions/<version_id>/duplicate")
def duplicate_api(version_id):
    payload=request.get_json(silent=True) or {}
    try:return jsonify(services().rubrics.duplicate(version_id,payload.get("name"))),201
    except LookupError as exc:return jsonify(error=str(exc)),404

@rubric_controller.put("/api/rubrics/<rubric_id>")
def update_api(rubric_id):
    payload=request.get_json(silent=True) or {}
    try:return jsonify(services().rubrics.update(rubric_id,payload.get("name",""),payload.get("description",""),payload.get("categories",[])))
    except LookupError as exc:return jsonify(error=str(exc)),404
    except PermissionError as exc:return jsonify(error=str(exc)),403

@rubric_controller.post("/api/rubrics/<rubric_id>/archive")
def archive_api(rubric_id):
    try:return jsonify(archived=services().rubrics.archive(rubric_id,True))
    except PermissionError as exc:return jsonify(error=str(exc)),403

@rubric_controller.delete("/api/rubrics/<rubric_id>")
def delete_api(rubric_id):
    try:return ("",204) if services().rubrics.delete(rubric_id) else (jsonify(error="Rubric not found."),404)
    except PermissionError as exc:return jsonify(error=str(exc)),403
    except ValueError as exc:return jsonify(error=str(exc)),409

class RubricController:blueprint=rubric_controller
