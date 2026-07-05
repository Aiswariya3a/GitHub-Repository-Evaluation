from database import connect


class RepositoryRepository:
    def add(self, session_id, roll_number, repo_url):
        with connect() as db:
            return db.execute("""INSERT INTO repositories(session_id,roll_number,repo_url)
                VALUES (%s,%s,%s) ON CONFLICT(session_id,repo_url) DO NOTHING RETURNING id""",
                (session_id, roll_number, repo_url)).fetchone()

    def list(self, session_id):
        with connect() as db:
            return db.execute("""SELECT r.*,e.id evaluation_id,e.total_out_of_80,e.normalized_to_20,
                e.overall_remarks,e.error evaluation_error,e.error_details
                FROM repositories r LEFT JOIN evaluations e ON e.repository_id=r.id
                WHERE r.session_id=%s ORDER BY r.created_at""", (session_id,)).fetchall()

    def get(self, session_id, repository_id):
        with connect() as db:
            return db.execute("""SELECT r.*,e.id evaluation_id,e.total_out_of_80,e.normalized_to_20,
                e.overall_remarks,e.error evaluation_error,e.error_details
                FROM repositories r LEFT JOIN evaluations e ON e.repository_id=r.id
                WHERE r.session_id=%s AND r.id=%s""", (session_id, repository_id)).fetchone()

    def queue(self, session_id, repository_id):
        with connect() as db:
            return bool(db.execute("""UPDATE repositories SET evaluation_status='Pending',error='',updated_at=now()
                WHERE id=%s AND session_id=%s""", (repository_id, session_id)).rowcount)

    def mark_running(self, repository_ids):
        with connect() as db:
            db.execute("UPDATE repositories SET evaluation_status='Evaluating',error='',updated_at=now() WHERE id=ANY(%s)", (repository_ids,))

    def mark_failed(self, repository_ids, error):
        with connect() as db:
            db.execute("""UPDATE repositories SET evaluation_status='Failed',error=%s,updated_at=now()
                WHERE id=ANY(%s) AND evaluation_status='Evaluating'""", (error, repository_ids))

    def recover_interrupted(self):
        with connect() as db:
            return db.execute("""UPDATE repositories SET evaluation_status='Pending',
                error='Previous evaluation was interrupted; ready to retry.',updated_at=now()
                WHERE evaluation_status='Evaluating'""").rowcount

    def save_analysis(self, repository_id, repo_data):
        with connect() as db:
            db.execute("""UPDATE repositories SET is_public=%s,readme_exists=%s,commit_count=%s,
                evaluation_status='Completed',error='',evaluated_at=now(),updated_at=now() WHERE id=%s""",
                (repo_data.get("public"), repo_data.get("readme_exists"), repo_data.get("commit_count"), repository_id))
