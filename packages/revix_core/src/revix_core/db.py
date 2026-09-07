"""Engine and session management.

One engine per process, created lazily so that importing the package does not
try to reach a database. Tests and the CLI both use session_scope; the API
uses get_session as a FastAPI dependency.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from revix_core.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    """One engine, with every wait bounded.

    Every timeout here exists because its absence turns a fast, legible
    failure into a hang, and a hang is the worst failure mode a demo can have.
    /health is written to report an unreachable database as a 503, but without
    connect_timeout it never gets the chance: psycopg waits on the operating
    system's TCP timeout, the platform's health probe gives up first, and the
    instance is marked unhealthy with nothing in the log explaining why.
    """
    settings = get_settings()
    return create_engine(
        settings.sync_database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        # A little headroom over pool_size rather than a hard wall, so a burst
        # queues briefly instead of erroring.
        max_overflow=settings.db_pool_size,
        # Neon can be asleep, and a sleeping database answers the TCP
        # handshake without completing the connection. This bounds that.
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle_seconds,
        # How long a request waits for a free connection before giving up.
        # SQLAlchemy defaults to thirty seconds, which is far longer than any
        # reader will wait: under load we would rather refuse quickly than
        # accumulate a queue of browsers that have already left.
        pool_timeout=settings.db_pool_timeout_seconds,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
        future=True,
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope. Commits on success, rolls back on any exception."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI dependency. Read-only by convention; the API never commits."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
