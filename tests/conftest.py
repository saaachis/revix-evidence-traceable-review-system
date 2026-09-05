"""Shared fixtures.

Database tests run inside a transaction that is always rolled back, so the
suite can be run repeatedly against a developer's local database without
leaving anything behind and without needing a teardown step to remember.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from revix_core.settings import get_settings

REQUIRED_EXTENSIONS = {"vector", "pg_trgm"}


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    dsn = os.environ.get("TEST_DATABASE_URL", get_settings().sync_database_url)
    eng = create_engine(dsn, future=True)
    try:
        with eng.connect() as conn:
            found = {r[0] for r in conn.execute(text("select extname from pg_extension")).all()}
        missing = REQUIRED_EXTENSIONS - found
        if missing:
            pytest.skip(f"database is missing extensions: {sorted(missing)}")
    except Exception as exc:  # pragma: no cover - only hit when there is no database
        pytest.skip(f"no database available: {exc}")
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose work is always rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    sess = Session(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield sess
    finally:
        sess.close()
        transaction.rollback()
        connection.close()
