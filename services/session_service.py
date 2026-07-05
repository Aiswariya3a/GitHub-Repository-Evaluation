from database import initialize_database
from repositories import SessionRepository


VALID_STATUSES = {"Active", "Completed", "Archived"}


class SessionService:
    """Session aggregate lifecycle; repository concerns live in RepositoryService."""

    def __init__(self, repository=None):
        initialize_database()
        self.repository = repository or SessionRepository()

    def create_session(self, name, description=""):
        name = str(name).strip()
        if not name:
            raise ValueError("Session name is required.")
        return self.repository.create(name, str(description).strip())

    def list_sessions(self): return self.repository.list()
    def get_session(self, session_id): return self.repository.get(session_id)
    def delete_session(self, session_id): return self.repository.delete(session_id)

    def set_status(self, session_id, status):
        if status not in VALID_STATUSES:
            raise ValueError("Invalid session status.")
        return self.repository.update_status(session_id, status)
