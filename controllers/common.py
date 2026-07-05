import json

from flask import abort, current_app


def services(): return current_app.extensions["services"]


def parse_evaluation(payload):
    if isinstance(payload, str):
        try: payload = json.loads(payload)
        except (TypeError, json.JSONDecodeError): payload = {}
    final = (payload or {}).get("final", {}) or {}
    total = float(final.get("total_out_of_80", 0) or 0)
    normalized = float(final.get("normalized_to_20", total / 4) or 0)
    label = "Strong" if normalized >= 16 else "On track" if normalized >= 12 else "Needs review" if normalized >= 8 else "Needs attention"
    return total, round(normalized, 2), str(final.get("overall_remarks", "Evaluation completed.")), label


def session_context(session_id):
    container = services(); session = container.sessions.get_session(session_id)
    if not session: abort(404)
    rows = []
    for repository in container.repositories.list_repositories(session_id):
        repo_data = repository["repo_data"]; evaluation = repository["evaluation_data"].get("evaluation", {})
        total, normalized, remarks, label = parse_evaluation(evaluation)
        is_public, has_readme = repo_data.get("public") is True, repo_data.get("readme_exists") is True
        status = repository["status"]
        if status == "Completed": status = "Blocked" if not is_public else "Missing README" if not has_readme else label
        rows.append({**repository, "repo": repository["repo_url"], "score": total, "normalized": normalized,
            "remarks": remarks, "display_status": status, "commit_count": repo_data.get("commit_count", 0),
            "public": is_public, "readme": has_readme,
            "progress": 100 if repository["status"] == "Completed" else 50 if repository["status"] == "Evaluating" else 8})
    completed = [row for row in rows if row["status"] == "Completed"]
    average = sum(row["normalized"] for row in completed) / len(completed) if completed else 0
    return session, rows, {"total": len(rows), "completed": len(completed),
        "pending": sum(row["status"] in {"Pending", "Failed"} for row in rows), "average": round(average, 1),
        "public": sum(row["public"] for row in completed), "readme": sum(row["readme"] for row in completed)}
