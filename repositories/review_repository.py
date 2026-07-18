from database import connect


class ReviewQueueRepository:
    def add(self, repository_id, session_id, flag_reason='low_confidence'):
        with connect() as db:
            return db.execute("""
                INSERT INTO review_queue(repository_id, session_id, flag_reason)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (repository_id, session_id, flag_reason)).fetchone()

    def get(self, repository_id, session_id):
        with connect() as db:
            return db.execute("""
                SELECT * FROM review_queue
                WHERE repository_id=%s AND session_id=%s
            """, (repository_id, session_id)).fetchone()

    def list_by_session(self, session_id, status=None):
        with connect() as db:
            if status:
                return db.execute("""
                    SELECT rq.*, r.roll_number, r.repo_url, r.evaluation_status
                    FROM review_queue rq
                    JOIN repositories r ON r.id = rq.repository_id
                    WHERE rq.session_id=%s AND rq.status=%s
                    ORDER BY rq.created_at DESC
                """, (session_id, status)).fetchall()
            return db.execute("""
                SELECT rq.*, r.roll_number, r.repo_url, r.evaluation_status
                FROM review_queue rq
                JOIN repositories r ON r.id = rq.repository_id
                WHERE rq.session_id=%s
                ORDER BY rq.created_at DESC
            """, (session_id,)).fetchall()

    def set_status(self, repository_id, session_id, status):
        with connect() as db:
            return bool(db.execute("""
                UPDATE review_queue SET status=%s, updated_at=now()
                WHERE repository_id=%s AND session_id=%s
            """, (status, repository_id, session_id)).rowcount)

    def pending_count(self, session_id):
        with connect() as db:
            row = db.execute("""
                SELECT COUNT(*) AS count FROM review_queue
                WHERE session_id=%s AND status='pending'
            """, (session_id,)).fetchone()
            return row["count"]

    def total_pending(self):
        with connect() as db:
            row = db.execute("""
                SELECT COUNT(*) AS count FROM review_queue
                WHERE status='pending'
            """).fetchone()
            return row["count"]

    def remove(self, repository_id, session_id):
        with connect() as db:
            return bool(db.execute("""
                DELETE FROM review_queue
                WHERE repository_id=%s AND session_id=%s
            """, (repository_id, session_id)).rowcount)


class ScoreOverrideRepository:
    def create(self, repository_id, session_id, criterion_key, original_score,
               overridden_score, reasoning, overridden_by='instructor'):
        with connect() as db:
            return db.execute("""
                INSERT INTO score_overrides(
                    repository_id, session_id, criterion_key,
                    original_score, overridden_score, reasoning, overridden_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                repository_id, session_id, criterion_key,
                original_score, overridden_score, reasoning, overridden_by
            )).fetchone()

    def list_by_repository(self, repository_id, session_id):
        with connect() as db:
            return db.execute("""
                SELECT * FROM score_overrides
                WHERE repository_id=%s AND session_id=%s
                ORDER BY created_at DESC
            """, (repository_id, session_id)).fetchall()

    def get_latest(self, repository_id, session_id):
        with connect() as db:
            return db.execute("""
                SELECT * FROM score_overrides
                WHERE repository_id=%s AND session_id=%s
                ORDER BY created_at DESC LIMIT 1
            """, (repository_id, session_id)).fetchone()


class AuditLogRepository:
    def append(self, repository_id, session_id, action, old_value='',
               new_value='', reasoning='', performed_by='instructor'):
        with connect() as db:
            return db.execute("""
                INSERT INTO audit_log(
                    repository_id, session_id, action,
                    old_value, new_value, reasoning, performed_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                repository_id, session_id, action,
                old_value, new_value, reasoning, performed_by
            )).fetchone()

    def list_by_repository(self, repository_id, session_id):
        with connect() as db:
            return db.execute("""
                SELECT * FROM audit_log
                WHERE repository_id=%s AND session_id=%s
                ORDER BY created_at DESC
            """, (repository_id, session_id)).fetchall()
