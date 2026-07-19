"""User-scoped persistence for essays and writing feedback."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.ai.schemas import WritingFeedbackSchema
from ielts_ai_coach.database.models import Essay, WritingFeedback


def create_essay(
    session: Session,
    *,
    user_id: int,
    test_type: str,
    task_type: str,
    prompt: str,
    content: str,
    word_count: int,
) -> Essay:
    """Create a pending essay owned by a user."""

    essay = Essay(
        user_id=user_id,
        test_type=test_type,
        task_type=task_type,
        prompt=prompt,
        content=content,
        word_count=word_count,
        status="pending",
    )
    session.add(essay)
    session.flush()
    return essay


def get_essay(
    session: Session, *, user_id: int, essay_id: int
) -> Essay | None:
    """Return an essay only when it belongs to the user."""

    statement = select(Essay).where(
        Essay.id == essay_id,
        Essay.user_id == user_id,
    )
    return session.scalar(statement)


def list_essays(
    session: Session, *, user_id: int, limit: int = 100
) -> list[Essay]:
    """Return one user's essay history from newest to oldest."""

    statement = (
        select(Essay)
        .where(Essay.user_id == user_id)
        .order_by(Essay.created_at.desc(), Essay.id.desc())
        .limit(max(1, min(limit, 500)))
    )
    return list(session.scalars(statement))


def set_essay_status(
    session: Session,
    *,
    user_id: int,
    essay_id: int,
    status: str,
    last_error: str = "",
) -> Essay | None:
    """Update status only for an essay owned by the user."""

    essay = get_essay(session, user_id=user_id, essay_id=essay_id)
    if essay is None:
        return None
    essay.status = status
    essay.last_error = last_error[:240]
    session.flush()
    return essay


def create_writing_feedback(
    session: Session,
    *,
    user_id: int,
    essay_id: int,
    feedback: WritingFeedbackSchema,
    provider: str,
    model_name: str,
) -> WritingFeedback:
    """Persist validated feedback for a user-owned essay."""

    record = WritingFeedback(
        user_id=user_id,
        essay_id=essay_id,
        provider=provider,
        model_name=model_name,
        raw_metadata={},
        **feedback.model_dump(),
    )
    session.add(record)
    session.flush()
    return record


def list_feedback_for_essay(
    session: Session, *, user_id: int, essay_id: int
) -> list[WritingFeedback]:
    """Return feedback only for a user-owned essay."""

    owned_essay = get_essay(session, user_id=user_id, essay_id=essay_id)
    if owned_essay is None:
        return []
    statement = (
        select(WritingFeedback)
        .where(
            WritingFeedback.user_id == user_id,
            WritingFeedback.essay_id == essay_id,
        )
        .order_by(WritingFeedback.created_at.desc(), WritingFeedback.id.desc())
    )
    return list(session.scalars(statement))


def list_user_writing_feedback(
    session: Session,
    *,
    user_id: int,
    limit: int = 100,
) -> list[WritingFeedback]:
    """Return one user's feedback history from newest to oldest."""

    statement = (
        select(WritingFeedback)
        .where(WritingFeedback.user_id == user_id)
        .order_by(WritingFeedback.created_at.desc(), WritingFeedback.id.desc())
        .limit(max(1, min(limit, 500)))
    )
    return list(session.scalars(statement))
