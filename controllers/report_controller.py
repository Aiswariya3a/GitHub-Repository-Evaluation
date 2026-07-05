from flask import Blueprint, abort, flash, redirect, send_file, url_for

from .common import services

report_controller = Blueprint("report", __name__)

def send_generated(temp, path, name):
    response = send_file(path, as_attachment=True, download_name=name); response.call_on_close(temp.cleanup); return response

@report_controller.get("/sessions/<session_id>/report")
def session_report(session_id):
    if not services().sessions.get_session(session_id): abort(404)
    try:
        temp,path=services().reports.generate(session_id); return send_generated(temp,path,f"session-{session_id}-report.pdf")
    except Exception as exc:
        flash(str(exc)); return redirect(url_for("session.detail", session_id=session_id))

@report_controller.get("/sessions/<session_id>/repositories/<repository_id>/report")
def repository_report(session_id, repository_id):
    if not services().sessions.get_session(session_id): abort(404)
    try:
        temp,path=services().reports.generate_repository(session_id,repository_id); return send_generated(temp,path,f"repository-{repository_id}-report.pdf")
    except Exception as exc:
        flash(str(exc)); return redirect(url_for("session.detail", session_id=session_id))

class ReportController:
    blueprint = report_controller
