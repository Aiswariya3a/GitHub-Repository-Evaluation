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
    schema = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")
    with connect() as db:
        db.execute(schema)
