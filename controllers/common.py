import json

from flask import abort, current_app


def services(): return current_app.extensions["services"]


def parse_evaluation(payload):
    if isinstance(payload, str):
        try: payload = json.loads(payload)
        except (TypeError, json.JSONDecodeError): payload = {}
    final = (payload or {}).get("final", {}) or {}
    total = float(final.get("total_score") or final.get("total_out_of_80", 0) or 0)
    normalized = float(final.get("normalized_to_20", total / 4) or 0)
    label = "Strong" if normalized >= 16 else "On track" if normalized >= 12 else "Needs review" if normalized >= 8 else "Needs attention"
    return total, round(normalized, 2), str(final.get("overall_remarks", "Evaluation completed.")), label


def _batch_commit_counts(repository_ids):
    """Fetch commits_count from ingestion_records for a batch of repository IDs."""
    from database import connect
    ids = [str(rid) for rid in repository_ids if rid]
    if not ids:
        return {}
    try:
        with connect() as db:
            rows = db.execute("""
                SELECT DISTINCT ON (repository_id) repository_id,
                    snapshot->'github_metadata'->>'commits_count' AS commits_count
                FROM ingestion_records
                WHERE repository_id = ANY(%s)
                ORDER BY repository_id, created_at DESC
            """, [ids])
            return {str(r["repository_id"]): int(r["commits_count"]) for r in rows if r["commits_count"]}
    except Exception:
        return {}


def session_context(session_id):
    container = services(); session = container.sessions.get_session(session_id)
    if not session: abort(404)
    rows = []
    for repository in container.repositories.list_repositories(session_id):
        repo_data = repository["repo_data"]; evaluation = repository["evaluation_data"].get("evaluation", {})
        total, normalized, remarks, label = parse_evaluation(evaluation)
        is_public, has_readme = repo_data.get("public") is True, repo_data.get("readme_exists") is True
        status = repository["status"]
        if status == "Completed": status = label
        rows.append({**repository, "repo": repository["repo_url"], "score": total, "normalized": normalized,
            "remarks": remarks, "display_status": status, "commit_count": repo_data.get("commit_count", 0),
            "public": is_public, "readme": has_readme,
            "language": repo_data.get("language", ""),
            "description": repo_data.get("description", ""),
            "stars_count": repo_data.get("stars_count", 0),
            "forks_count": repo_data.get("forks_count", 0),
            "topics": repo_data.get("topics", []),
            "license_info": repo_data.get("license_info", ""),
            "open_issues_count": repo_data.get("open_issues_count", 0),
            "watchers_count": repo_data.get("watchers_count", 0),
            "size": repo_data.get("size", 0),
            "default_branch": repo_data.get("default_branch", ""),
            "progress": repository.get("progress_pct", 100 if repository["status"] == "Completed" else 50 if repository["status"] == "Evaluating" else 0),
            "current_step": repository.get("current_step", "")})
    ingestion_commits = _batch_commit_counts([r.get("id") for r in rows])
    for row in rows:
        rid = str(row.get("id", ""))
        if rid in ingestion_commits and ingestion_commits[rid] > (row.get("commit_count") or 0):
            row["commit_count"] = ingestion_commits[rid]
    # Fetch low_confidence flags from evaluation_results
    try:
        for row in rows:
            rid = str(row.get("id", ""))
            if rid:
                eval_result = container.repositories.evaluations.get_evaluation_result(rid, session_id)
                if eval_result:
                    row["has_low_confidence"] = bool(eval_result.get("low_confidence_criteria"))
                else:
                    row["has_low_confidence"] = False
            else:
                row["has_low_confidence"] = False
    except Exception:
        for row in rows:
            row["has_low_confidence"] = False
    # Fetch plagiarism data for the session
    plagiarism = []
    try:
        plagiarism = container.repositories.plagiarism(session_id) or []
    except Exception:
        pass
    completed = [row for row in rows if row["status"] == "Completed"]
    average = sum(row["normalized"] for row in completed) / len(completed) if completed else 0
    return session, rows, {"total": len(rows), "completed": len(completed),
        "pending": sum(row["status"] in {"Pending", "Failed"} for row in rows), "average": round(average, 1),
        "public": sum(row["public"] for row in completed), "readme": sum(row["readme"] for row in completed)}, plagiarism
