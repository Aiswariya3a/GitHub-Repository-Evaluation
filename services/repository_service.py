from repositories import EvaluationRepository, RepositoryRepository, SessionRepository


class RepositoryService:
    def __init__(self, repositories=None, evaluations=None, sessions=None):
        self.repository = repositories or RepositoryRepository()
        self.evaluations = evaluations or EvaluationRepository()
        self.sessions = sessions or SessionRepository()

    def add_repositories(self, session_id, entries):
        session = self.sessions.get(session_id)
        if not session:
            raise LookupError("Session not found.")
        if session["status"] != "Active":
            raise ValueError("Repositories can only be added to an active session.")
        added = sum(bool(self.repository.add(session_id, item["roll"], item["repo"])) for item in entries)
        self.sessions.touch(session_id)
        return added

    def _hydrate(self, row):
        if not row: return None
        evaluation = self.evaluations.hydrate(row)
        row["status"] = row["evaluation_status"]
        row["repo_data"] = {"roll_number": row["roll_number"], "repo": row["repo_url"], "public": row["is_public"], "readme_exists": row["readme_exists"], "commit_count": row["commit_count"]}
        row["evaluation_data"] = {"roll_number": row["roll_number"], "repo": row["repo_url"], "evaluation": evaluation}
        return row

    def list_repositories(self, session_id): return [self._hydrate(row) for row in self.repository.list(session_id)]
    def get_repository(self, session_id, repository_id): return self._hydrate(self.repository.get(session_id, repository_id))
    def pending_repositories(self, session_id): return [row for row in self.list_repositories(session_id) if row["status"] in {"Pending", "Failed"}]
    def queue_repository(self, session_id, repository_id): return self.repository.queue(session_id, repository_id)
    def mark_running(self, ids): self.repository.mark_running(ids)
    def mark_failed(self, ids, error): self.repository.mark_failed(ids, error)
    def recover_interrupted_evaluations(self): return self.repository.recover_interrupted()

    def save_repository_evaluation(self, repository_id, repo_data, evaluation):
        self.evaluations.save(repository_id, evaluation)
        self.repository.save_analysis(repository_id, repo_data)

    def save_plagiarism(self, session_id, rows): self.evaluations.save_plagiarism(session_id, rows)
    def plagiarism(self, session_id): return self.evaluations.plagiarism(session_id)
