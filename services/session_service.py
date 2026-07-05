from database import initialize_database
from repositories import SessionRepository


VALID_STATUSES = {"Active", "Completed", "Archived"}


class SessionService:
    """Session aggregate lifecycle; repository concerns live in RepositoryService."""

    def __init__(self, repository=None, default_rubric_version_id=None):
        initialize_database()
        self.repository = repository or SessionRepository()
        self.default_rubric_version_id=default_rubric_version_id

    def create_session(self, name, description="", rubric_version_id=None):
        name = str(name).strip()
        if not name:
            raise ValueError("Session name is required.")
        version_id=rubric_version_id or self.default_rubric_version_id
        if not version_id: raise ValueError("A rubric is required for every session.")
        return self.repository.create(name, str(description).strip(), version_id)

    def list_sessions(self): return self.repository.list()
    def get_session(self, session_id): return self.repository.get(session_id)
    def delete_session(self, session_id): return self.repository.delete(session_id)

    def set_status(self, session_id, status):
        if status not in VALID_STATUSES:
            raise ValueError("Invalid session status.")
        return self.repository.update_status(session_id, status)
