"""Database connections and schema migrations."""

from __future__ import annotations

import logging
from importlib import resources

import psycopg

log = logging.getLogger(__name__)

_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now()
)
"""

# Any constant works; it only has to be the same for every Pillmark process.
_MIGRATION_LOCK = 0x50494C4C  # "PILL"


def connect(url: str, *, autocommit: bool = False) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(url, autocommit=autocommit, application_name="pillmark")


def migration_files() -> list[tuple[str, str]]:
    """``(version, sql)`` for every bundled migration, in order."""
    folder = resources.files("pillmark") / "migrations"
    found = [
        (entry.name.removesuffix(".sql"), entry.read_text("utf-8"))
        for entry in folder.iterdir()
        if entry.name.endswith(".sql")
    ]
    return sorted(found)


def migrate(url: str) -> list[str]:
    """Apply pending migrations and return the versions applied."""
    applied: list[str] = []
    with connect(url) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK,))
        try:
            conn.execute(_MIGRATIONS_TABLE)
            done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
            conn.commit()
            for version, sql in migration_files():
                if version in done:
                    continue
                log.info("applying migration %s", version)
                with conn.transaction():
                    conn.execute(sql.encode())
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
                applied.append(version)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK,))
            conn.commit()
    return applied
