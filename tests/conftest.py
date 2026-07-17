"""Shared pytest fixtures for the V1 authentication foundation."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import create_database_engine
from ielts_ai_coach.database.models import Base


@pytest.fixture()
def test_database_url(tmp_path: Path) -> str:
    """Return an isolated SQLite URL for one test."""

    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture()
def session_factory(
    test_database_url: str,
) -> sessionmaker[Session]:
    """Return a session factory with a fresh users table."""

    engine = create_database_engine(test_database_url)
    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
    )
    yield factory
    engine.dispose()
