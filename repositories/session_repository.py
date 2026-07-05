from database import connect


class SessionRepository:
    def create(self, name, description):
        with connect() as db:
            return db.execute("INSERT INTO evaluation_sessions(name,description) VALUES (%s,%s) RETURNING *", (name, description)).fetchone()

    def list(self):
        with connect() as db:
            return db.execute("""SELECT s.*,COUNT(r.id) repository_count,
                COUNT(r.id) FILTER (WHERE r.evaluation_status='Completed') evaluated_count
                FROM evaluation_sessions s LEFT JOIN repositories r ON r.session_id=s.id
                GROUP BY s.id ORDER BY s.created_at DESC""").fetchall()

    def get(self, session_id):
        with connect() as db:
            return db.execute("SELECT * FROM evaluation_sessions WHERE id=%s", (session_id,)).fetchone()

    def update_status(self, session_id, status):
        with connect() as db:
            return bool(db.execute("UPDATE evaluation_sessions SET status=%s,updated_at=now() WHERE id=%s", (status, session_id)).rowcount)

    def touch(self, session_id):
        with connect() as db:
            db.execute("UPDATE evaluation_sessions SET updated_at=now() WHERE id=%s", (session_id,))

    def delete(self, session_id):
        with connect() as db:
            return bool(db.execute("DELETE FROM evaluation_sessions WHERE id=%s", (session_id,)).rowcount)
