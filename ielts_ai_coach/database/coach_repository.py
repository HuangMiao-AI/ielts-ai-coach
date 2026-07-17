"""User-scoped persistence for AI coach messages."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.models import CoachMessage


def create_coach_message(
    session: Session,
    *,
    user_id: int,
    role: str,
    content: str,
    provider: str = "",
    model_name: str = "",
) -> CoachMessage:
    """Create one coach message owned by a user."""

    message = CoachMessage(
        user_id=user_id,
        role=role,
        content=content,
        provider=provider,
        model_name=model_name,
        is_visible=True,
    )
    session.add(message)
    session.flush()
    return message


def list_recent_visible_messages(
    session: Session, *, user_id: int, limit: int = 6
) -> list[CoachMessage]:
    """Return a user's recent visible messages in chronological order."""

    statement = (
        select(CoachMessage)
        .where(
            CoachMessage.user_id == user_id,
            CoachMessage.is_visible.is_(True),
        )
        .order_by(CoachMessage.created_at.desc(), CoachMessage.id.desc())
        .limit(max(1, min(limit, 100)))
    )
    return list(reversed(list(session.scalars(statement))))


def list_coach_history(
    session: Session, *, user_id: int, limit: int = 200
) -> list[CoachMessage]:
    """Return a user's complete coach history, newest first."""

    statement = (
        select(CoachMessage)
        .where(CoachMessage.user_id == user_id)
        .order_by(CoachMessage.created_at.desc(), CoachMessage.id.desc())
        .limit(max(1, min(limit, 1000)))
    )
    return list(session.scalars(statement))


def hide_visible_messages(session: Session, user_id: int) -> int:
    """Hide the current conversation while preserving user history."""

    statement = select(CoachMessage).where(
        CoachMessage.user_id == user_id,
        CoachMessage.is_visible.is_(True),
    )
    messages = list(session.scalars(statement))
    for message in messages:
        message.is_visible = False
    return len(messages)
