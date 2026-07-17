"""User-scoped deletion operations for optional student-owned data."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ielts_ai_coach.database.models import (
    CoachMessage,
    Essay,
    PlanTask,
    ScoreRecord,
    StudyLog,
    StudyPlan,
    TaskQuestionAttempt,
    WritingFeedback,
)


@dataclass(frozen=True)
class DeletionCounts:
    """Counts of records removed from user-owned data tables."""

    scores: int = 0
    plans: int = 0
    tasks: int = 0
    logs: int = 0
    essays: int = 0
    feedback: int = 0
    messages: int = 0
    attempts: int = 0


def delete_learning_records(session: Session, user_id: int) -> DeletionCounts:
    """Delete scores, plans, tasks, and logs owned by one user."""

    attempt_count = session.execute(
        delete(TaskQuestionAttempt).where(
            TaskQuestionAttempt.user_id == user_id
        )
    ).rowcount
    log_count = session.execute(
        delete(StudyLog).where(StudyLog.user_id == user_id)
    ).rowcount
    task_count = session.execute(
        delete(PlanTask).where(PlanTask.user_id == user_id)
    ).rowcount
    plan_count = session.execute(
        delete(StudyPlan).where(StudyPlan.user_id == user_id)
    ).rowcount
    score_count = session.execute(
        delete(ScoreRecord).where(ScoreRecord.user_id == user_id)
    ).rowcount
    return DeletionCounts(
        scores=score_count,
        plans=plan_count,
        tasks=task_count,
        logs=log_count,
        attempts=attempt_count,
    )


def delete_ai_content(session: Session, user_id: int) -> DeletionCounts:
    """Delete essays, feedback, and coach messages owned by one user."""

    feedback_count = session.execute(
        delete(WritingFeedback).where(WritingFeedback.user_id == user_id)
    ).rowcount
    essay_count = session.execute(
        delete(Essay).where(Essay.user_id == user_id)
    ).rowcount
    message_count = session.execute(
        delete(CoachMessage).where(CoachMessage.user_id == user_id)
    ).rowcount
    return DeletionCounts(
        essays=essay_count,
        feedback=feedback_count,
        messages=message_count,
    )
