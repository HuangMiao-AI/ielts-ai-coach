"""User-scoped persistence for deterministic reading submissions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.models import TaskQuestionAttempt


def create_task_question_attempt(
    session: Session,
    *,
    user_id: int,
    task_id: int,
    passage_id: str,
    passage_version: str,
    answers_json: str,
    results_json: str,
    score: int,
    total_questions: int,
    accuracy: float,
    incorrect_question_ids_json: str,
) -> TaskQuestionAttempt:
    """Create one final scored submission for a user-owned task."""

    attempt = TaskQuestionAttempt(
        user_id=user_id,
        task_id=task_id,
        passage_id=passage_id,
        passage_version=passage_version,
        answers_json=answers_json,
        results_json=results_json,
        score=score,
        total_questions=total_questions,
        accuracy=accuracy,
        incorrect_question_ids_json=incorrect_question_ids_json,
    )
    session.add(attempt)
    session.flush()
    return attempt


def get_task_question_attempt(
    session: Session,
    *,
    user_id: int,
    task_id: int,
) -> TaskQuestionAttempt | None:
    """Return a submission only when both user and task identifiers match."""

    statement = select(TaskQuestionAttempt).where(
        TaskQuestionAttempt.user_id == user_id,
        TaskQuestionAttempt.task_id == task_id,
    )
    return session.scalar(statement)


def list_task_question_attempts(
    session: Session,
    *,
    user_id: int,
    limit: int = 100,
) -> list[TaskQuestionAttempt]:
    """Return a user's newest reading submissions."""

    statement = (
        select(TaskQuestionAttempt)
        .where(TaskQuestionAttempt.user_id == user_id)
        .order_by(
            TaskQuestionAttempt.submitted_at.desc(),
            TaskQuestionAttempt.id.desc(),
        )
        .limit(max(1, min(limit, 200)))
    )
    return list(session.scalars(statement))
