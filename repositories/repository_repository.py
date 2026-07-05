from database import connect


class RepositoryRepository:
    def add(self, session_id, roll_number, repo_url):
        with connect() as db:
            return db.execute("""INSERT INTO repositories(session_id,roll_number,repo_url)
                VALUES (%s,%s,%s) ON CONFLICT(session_id,repo_url) DO NOTHING RETURNING id""",
                (session_id, roll_number, repo_url)).fetchone()

    def list(self, session_id):
        with connect() as db:
            return db.execute("""SELECT r.*,e.id evaluation_id,e.total_out_of_80,e.total_score,e.max_score,e.normalized_to_20,
                e.rubric_version_id evaluation_rubric_version_id,e.overall_remarks,e.error evaluation_error,e.error_details
                FROM repositories r LEFT JOIN evaluations e ON e.repository_id=r.id
                WHERE r.session_id=%s ORDER BY r.created_at""", (session_id,)).fetchall()

    def get(self, session_id, repository_id):
        with connect() as db:
            return db.execute("""SELECT r.*,e.id evaluation_id,e.total_out_of_80,e.total_score,e.max_score,e.normalized_to_20,
                e.rubric_version_id evaluation_rubric_version_id,e.overall_remarks,e.error evaluation_error,e.error_details
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

    def dashboard_metrics(self):
        with connect() as db:
            metrics = db.execute("""SELECT COUNT(DISTINCT s.id) session_count,COUNT(r.id) repository_count,
                COUNT(r.id) FILTER(WHERE r.evaluation_status='Completed') evaluated_count,
                COUNT(r.id) FILTER(WHERE r.evaluation_status='Evaluating') running_count,
                COALESCE(AVG(e.normalized_to_20),0) average_health
                FROM evaluation_sessions s LEFT JOIN repositories r ON r.session_id=s.id
                LEFT JOIN evaluations e ON e.repository_id=r.id""").fetchone()
            recent = db.execute("""SELECT r.id,r.session_id,r.roll_number,r.repo_url,r.evaluation_status,
                r.updated_at,s.name session_name,e.normalized_to_20
                FROM repositories r JOIN evaluation_sessions s ON s.id=r.session_id
                LEFT JOIN evaluations e ON e.repository_id=r.id ORDER BY r.updated_at DESC LIMIT 8""").fetchall()
            running = db.execute("""SELECT r.id,r.session_id,r.roll_number,r.repo_url,r.updated_at,s.name session_name
                FROM repositories r JOIN evaluation_sessions s ON s.id=r.session_id
                WHERE r.evaluation_status='Evaluating' ORDER BY r.updated_at""").fetchall()
            leaderboard = db.execute("""SELECT r.id,r.session_id,r.roll_number,r.repo_url,e.normalized_to_20,
                e.overall_remarks,s.name session_name FROM repositories r JOIN evaluations e ON e.repository_id=r.id
                JOIN evaluation_sessions s ON s.id=r.session_id WHERE r.evaluation_status='Completed'
                ORDER BY e.normalized_to_20 DESC NULLS LAST LIMIT 8""").fetchall()
            score_distribution = db.execute("""SELECT
                COUNT(*) FILTER(WHERE normalized_to_20<8) low,
                COUNT(*) FILTER(WHERE normalized_to_20>=8 AND normalized_to_20<12) review,
                COUNT(*) FILTER(WHERE normalized_to_20>=12 AND normalized_to_20<16) track,
                COUNT(*) FILTER(WHERE normalized_to_20>=16) strong FROM evaluations""").fetchone()
            technologies = db.execute("""SELECT name,COUNT(*) count FROM technologies GROUP BY name
                ORDER BY count DESC,name LIMIT 10""").fetchall()
        return metrics, recent, running, leaderboard, score_distribution, technologies

    def related_data(self, repository_id):
        tables = ("code_quality", "documentation", "collaboration", "project_health", "technologies",
                  "contributors", "commits", "pull_requests", "issues", "files")
        with connect() as db:
            return {table: db.execute(f"SELECT * FROM {table} WHERE repository_id=%s ORDER BY created_at DESC", (repository_id,)).fetchall() for table in tables}

    def technologies_for_session(self, session_id):
        with connect() as db:
            return db.execute("""SELECT t.name,COUNT(*) count FROM technologies t
                JOIN repositories r ON r.id=t.repository_id WHERE r.session_id=%s
                GROUP BY t.name ORDER BY count DESC,t.name""", (session_id,)).fetchall()

    def search(self, query):
        pattern = f"%{query}%"
        with connect() as db:
            sessions = db.execute("""SELECT id,name label,status hint FROM evaluation_sessions
                WHERE name ILIKE %s OR description ILIKE %s ORDER BY updated_at DESC LIMIT 6""", (pattern, pattern)).fetchall()
            repositories = db.execute("""SELECT r.id,r.session_id,r.roll_number label,r.repo_url hint
                FROM repositories r WHERE r.roll_number ILIKE %s OR r.repo_url ILIKE %s
                ORDER BY r.updated_at DESC LIMIT 8""", (pattern, pattern)).fetchall()
        return sessions, repositories
