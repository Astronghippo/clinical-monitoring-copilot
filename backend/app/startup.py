"""Lightweight startup hooks run before uvicorn boots.

Keeps prototype-level schema in sync without pulling in full Alembic machinery.
For Postgres, uses `ADD COLUMN IF NOT EXISTS` which is safe to run repeatedly.
For SQLite (tests), `Base.metadata.create_all()` already creates fresh tables
with all columns, so no explicit ALTER is needed.
"""
from __future__ import annotations

from sqlalchemy import text

from app.db import Base, engine
from app import models  # noqa: F401  — register ORM classes


# Additive schema patches. Each item is (table, column_def_sql) applied via
# ADD COLUMN IF NOT EXISTS on Postgres only.
_PG_ADDITIVE_PATCHES: list[tuple[str, str]] = [
    ("protocols", "parse_status VARCHAR(16) DEFAULT 'done'"),
    ("protocols", "parse_error TEXT"),
    ("protocols", "summary_json JSONB"),
]


def ensure_schema() -> None:
    """Create tables that don't exist; patch in new columns on Postgres."""
    Base.metadata.create_all(engine)

    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            for table, column_def in _PG_ADDITIVE_PATCHES:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column_def}")
                )
