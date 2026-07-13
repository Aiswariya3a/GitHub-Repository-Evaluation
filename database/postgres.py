from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def database_url():
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL is required. Add the PostgreSQL connection URL to .env.")
    return value


def connect():
    return psycopg.connect(database_url(), row_factory=dict_row)


def initialize_database():
    db_dir = Path(__file__).parent
    schema = (db_dir / "schema.sql").read_text(encoding="utf-8")
    with connect() as db:
        db.execute(schema)
    for migration in sorted(db_dir.glob("migration_*.sql")):
        try:
            sql = migration.read_text(encoding="utf-8")
            with connect() as db:
                db.execute(sql)
        except Exception:
            pass
