"""SQLAlchemy engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.config import get_database_url
from ielts_ai_coach.database.models import Base


def _prepare_sqlite_directory(database_url: str) -> None:
    """Create the parent directory for a file-based SQLite database."""

    parsed_url = make_url(database_url)
    if not parsed_url.drivername.startswith("sqlite"):
        return
    if parsed_url.database in (None, "", ":memory:"):
        return
    Path(parsed_url.database).expanduser().resolve().parent.mkdir(
        parents=True, exist_ok=True
    )


def create_database_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine configured for the selected database."""

    _prepare_sqlite_directory(database_url)
    is_sqlite = make_url(database_url).drivername.startswith("sqlite")
    connect_args = (
        {"check_same_thread": False, "timeout": 30}
        if is_sqlite
        else {}
    )
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def configure_sqlite(database_connection: object, _: object) -> None:
            """Enable SQLite foreign keys and write-ahead logging."""

            cursor = database_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


@lru_cache(maxsize=8)
def get_engine(database_url: str) -> Engine:
    """Return a cached database engine for a database URL."""

    return create_database_engine(database_url)


@lru_cache(maxsize=8)
def _get_session_factory(database_url: str) -> sessionmaker[Session]:
    """Build and cache a session factory for one resolved database URL."""

    return sessionmaker(
        bind=get_engine(database_url),
        class_=Session,
        expire_on_commit=False,
    )


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Return a cached session factory for the current resolved URL."""

    active_url = database_url or get_database_url()
    return _get_session_factory(active_url)


@contextmanager
def session_scope(
    session_factory: sessionmaker[Session] | None = None,
) -> Iterator[Session]:
    """Provide a transaction scope that commits or rolls back safely."""

    factory = session_factory or get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def initialize_database(database_url: str | None = None) -> None:
    """Create all active tables when they do not already exist."""

    active_url = database_url or get_database_url()
    Base.metadata.create_all(get_engine(active_url))
