from __future__ import annotations

import os
from collections.abc import Iterator

import psycopg
import pytest

from pillmark.db import migrate

TEST_DB_ENV = "PILLMARK_TEST_DATABASE_URL"


@pytest.fixture(scope="session")
def db_url() -> str:
    """A migrated, empty database. Tests that need it are skipped without one."""
    url = os.environ.get(TEST_DB_ENV)
    if not url:
        pytest.skip(f"set {TEST_DB_ENV} to run database tests")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
    migrate(url)
    return url


@pytest.fixture
def clean_db(db_url: str) -> str:
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("TRUNCATE labels, pills, import_runs RESTART IDENTITY CASCADE")
    return db_url


@pytest.fixture
def conn(clean_db: str) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
    with psycopg.connect(clean_db) as connection:
        yield connection
