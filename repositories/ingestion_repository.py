from datetime import datetime, timezone

from psycopg.types.json import Jsonb

from database import connect


class IngestionRepository:
    def save_ingestion(
        self,
        repository_id: str,
        snapshot_dict: dict,
        ingestion_version: str = "1.0",
    ) -> str | None:
        repo_stats = snapshot_dict.get("repo_stats", {})
        total_loc = repo_stats.get("total_loc", 0)
        file_count = repo_stats.get("file_count", 0)
        language_breakdown = repo_stats.get("language_breakdown", {})
        status = snapshot_dict.get("repository_metadata", {}).get("status", "pending")

        with connect() as db:
            result = db.execute(
                """INSERT INTO ingestion_records
                   (repository_id, snapshot, total_loc, file_count,
                    language_breakdown, status, ingestion_version, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                   RETURNING id""",
                [
                    repository_id,
                    Jsonb(snapshot_dict),
                    total_loc,
                    file_count,
                    Jsonb(language_breakdown),
                    status,
                    ingestion_version,
                ],
            )
            row = result.fetchone()
            return str(row["id"]) if row else None

    def get_ingestion(self, repository_id: str) -> dict | None:
        try:
            with connect() as db:
                result = db.execute(
                    """SELECT * FROM ingestion_records
                       WHERE repository_id = %s
                       ORDER BY created_at DESC
                       LIMIT 1""",
                    [repository_id],
                )
                return result.fetchone()
        except Exception:
            return None

    def get_ingestion_by_id(self, record_id: str) -> dict | None:
        with connect() as db:
            result = db.execute(
                "SELECT * FROM ingestion_records WHERE id = %s",
                [record_id],
            )
            return result.fetchone()

    def get_all_for_repository(self, repository_id: str) -> list[dict]:
        with connect() as db:
            result = db.execute(
                """SELECT * FROM ingestion_records
                   WHERE repository_id = %s
                   ORDER BY created_at ASC""",
                [repository_id],
            )
            return result.fetchall()

    def update_status(
        self, record_id: str, status: str, error: str | None = None
    ) -> bool:
        valid_statuses = {"pending", "success", "failed", "partial"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

        with connect() as db:
            result = db.execute(
                """UPDATE ingestion_records
                   SET status = %s, error = %s, updated_at = NOW()
                   WHERE id = %s""",
                [status, error, record_id],
            )
            return result.rowcount > 0
