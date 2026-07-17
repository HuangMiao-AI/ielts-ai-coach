"""Safe deletion services for the authenticated user's optional data."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.data_repository import (
    DeletionCounts,
    delete_ai_content,
    delete_learning_records,
)


def clear_learning_records(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> DeletionCounts:
    """Delete only the selected user's scores, plans, tasks, and logs."""

    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        return delete_learning_records(session, user_id)


def clear_ai_content(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> DeletionCounts:
    """Delete only the selected user's essays, feedback, and coach messages."""

    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        return delete_ai_content(session, user_id)
