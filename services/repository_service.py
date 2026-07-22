from services.github_service import GitHubService
from repositories import EvaluationRepository, IngestionRepository, RepositoryRepository, SessionRepository


class RepositoryService:
    def __init__(self, repositories=None, evaluations=None, sessions=None, github_service=None, ingestion_repo=None):
        self.repository = repositories or RepositoryRepository()
        self.evaluations = evaluations or EvaluationRepository()
        self.sessions = sessions or SessionRepository()
        self.github = github_service or GitHubService()
        self.ingestion_repo = ingestion_repo or IngestionRepository()

    def add_repositories(self, session_id, entries):
        session = self.sessions.get(session_id)
        if not session:
            raise LookupError("Session not found.")
        if session["status"] != "Active":
            raise ValueError("Repositories can only be added to an active session.")
        added = []
        for item in entries:
            row = self.repository.add(session_id, item["roll"], item["repo"])
            if row:
                repo_id = str(row["id"])
                meta = self.github.get_repo_metadata(item["repo"]) or {}
                self.repository.update_github_metadata(repo_id, meta)
                added.append({"id": repo_id, "roll_number": item["roll"], "repo_url": item["repo"], **meta})
        self.sessions.touch(session_id)
        return added

    def _hydrate(self, row):
        if not row: return None
        evaluation = self.evaluations.hydrate(row)
        row["status"] = row["evaluation_status"]
        row["progress_pct"] = row.get("progress_pct", 0)
        row["current_step"] = row.get("current_step", "")
        row["repo_data"] = {
            "roll_number": row["roll_number"], "repo": row["repo_url"],
            "public": row["is_public"], "readme_exists": row["readme_exists"],
            "commit_count": row["commit_count"],
            "language": row.get("language", ""),
            "description": row.get("description", ""),
            "stars_count": row.get("stars_count", 0),
            "forks_count": row.get("forks_count", 0),
            "topics": row.get("topics", []),
            "license_info": row.get("license_info", ""),
            "open_issues_count": row.get("open_issues_count", 0),
            "watchers_count": row.get("watchers_count", 0),
            "size": row.get("size", 0),
            "default_branch": row.get("default_branch", ""),
        }
        row["evaluation_data"] = {"roll_number": row["roll_number"], "repo": row["repo_url"], "evaluation": evaluation}
        return row

    def list_repositories(self, session_id): return [self._hydrate(row) for row in self.repository.list(session_id)]
    def get_repository(self, session_id, repository_id): return self._hydrate(self.repository.get(session_id, repository_id))
    def pending_repositories(self, session_id): return [row for row in self.list_repositories(session_id) if row["status"] in {"Pending", "Failed"}]
    def delete_repository(self, session_id, repository_id): return self.repository.delete(session_id, repository_id)

    def queue_repository(self, session_id, repository_id): return self.repository.queue(session_id, repository_id)
    def mark_running(self, ids): self.repository.mark_running(ids)
    def mark_failed(self, ids, error): self.repository.mark_failed(ids, error)
    def update_progress(self, repository_id, pct, step): self.repository.update_progress(repository_id, pct, step)
    def recover_interrupted_evaluations(self): return self.repository.recover_interrupted()

    def save_repository_evaluation(self, repository_id, repo_data, evaluation, rubric_version_id):
        self.evaluations.save(repository_id, evaluation, rubric_version_id)
        self.repository.save_analysis(repository_id, repo_data)

    def save_plagiarism(self, session_id, rows): self.evaluations.save_plagiarism(session_id, rows)
    def plagiarism(self, session_id): return self.evaluations.plagiarism(session_id)

    def dashboard(self):
        metrics, recent, running, leaderboard, distribution, technologies = self.repository.dashboard_metrics()
        return {"metrics": metrics, "recent_activity": recent, "running_evaluations": running,
                "leaderboard": leaderboard, "score_distribution": distribution, "technologies": technologies}

    def repository_detail(self, session_id, repository_id):
        repository = self.get_repository(session_id, repository_id)
        if not repository: return None
        try:
            ingestion = self.ingestion_repo.get_ingestion(repository_id)
            if ingestion:
                snap = ingestion.get("snapshot") or {}
                repository["ingestion"] = {
                    "repo_stats": snap.get("repo_stats", {}),
                    "files": snap.get("files", []),
                    "github_metadata": snap.get("github_metadata", {}),
                    "repository_metadata": snap.get("repository_metadata", {}),
                }
        except Exception:
            pass
        try:
            evaluation = self.evaluations.get_evaluation_result(repository_id, session_id)
            if evaluation:
                repository["evaluation_result"] = evaluation
        except Exception:
            pass
        try:
            repository["insights"] = self.repository.related_data(repository_id)
        except Exception:
            repository["insights"] = {}
        try:
            from services.review_service import ReviewService
            repository["overrides"] = ReviewService().get_overrides(repository_id, session_id)
        except Exception:
            repository["overrides"] = []
        return repository

    def session_insights(self, session_id):
        rows = self.list_repositories(session_id)
        completed = [row for row in rows if row["status"] == "Completed"]
        distribution = {"0-7": 0, "8-11": 0, "12-15": 0, "16-20": 0}
        for row in completed:
            score = float(row.get("normalized_to_20") or 0)
            distribution["0-7" if score < 8 else "8-11" if score < 12 else "12-15" if score < 16 else "16-20"] += 1
        timeline = sorted(({"repository_id": row["id"], "roll_number": row["roll_number"], "repo_url": row["repo_url"],
            "status": row["status"], "at": row["evaluated_at"] or row["updated_at"]} for row in rows), key=lambda item: item["at"], reverse=True)[:12]
        return {"score_distribution": distribution, "technologies": self.repository.technologies_for_session(session_id), "timeline": timeline}

    def search(self, query):
        sessions, repositories = self.repository.search(query)
        return ([{"label": row["label"], "hint": f"{row['hint']} session", "url": f"/sessions/{row['id']}"} for row in sessions] +
                [{"label": row["label"], "hint": row["hint"], "url": f"/sessions/{row['session_id']}/repositories/{row['id']}"} for row in repositories])
