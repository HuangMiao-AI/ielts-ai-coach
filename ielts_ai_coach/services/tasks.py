"""User-scoped task completion and study-log services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.exercise_repository import (
    get_task_question_attempt,
)
from ielts_ai_coach.database.models import PlanTask, StudyLog
from ielts_ai_coach.database.plan_repository import (
    list_study_logs,
    list_tasks_for_date,
    set_task_completed,
    set_task_pending,
)
from ielts_ai_coach.services.planning import get_active_plan_data


MAX_ACTUAL_MINUTES = 720


class TaskUpdateError(ValueError):
    """Raised when a task update is invalid or unauthorized."""


@dataclass(frozen=True)
class WeekProgress:
    """Completion and study-time metrics for one seven-day plan."""

    total_tasks: int
    completed_tasks: int
    planned_minutes: int
    actual_minutes: int
    completion_rate: float


def get_tasks_for_day(
    user_id: int,
    *,
    task_date: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> list[PlanTask]:
    """Return active-plan tasks owned by a user for one day."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return list_tasks_for_date(
            session,
            user_id=user_id,
            task_date=task_date or date.today(),
        )


def complete_task(
    *,
    user_id: int,
    task_id: int,
    actual_minutes: int | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> PlanTask:
    """Complete a task, defaulting actual time to its planned minutes."""

    if actual_minutes is not None and not (
        1 <= actual_minutes <= MAX_ACTUAL_MINUTES
    ):
        raise TaskUpdateError("invalid_minutes")
    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        task = set_task_completed(
            session,
            user_id=user_id,
            task_id=task_id,
            actual_minutes=actual_minutes,
        )
        if task is None:
            raise TaskUpdateError("task_not_found")
        return task


def cancel_task_completion(
    *,
    user_id: int,
    task_id: int,
    session_factory: sessionmaker[Session] | None = None,
) -> PlanTask:
    """Return a user-owned completed task to pending state."""

    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        if get_task_question_attempt(
            session,
            user_id=user_id,
            task_id=task_id,
        ) is not None:
            raise TaskUpdateError("practice_submission_locked")
        task = set_task_pending(
            session,
            user_id=user_id,
            task_id=task_id,
        )
        if task is None:
            raise TaskUpdateError("task_not_found")
        return task


def get_study_logs(
    user_id: int,
    *,
    start_date: date,
    end_date: date,
    session_factory: sessionmaker[Session] | None = None,
) -> list[StudyLog]:
    """Return user-owned learning logs within an inclusive range."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return list_study_logs(
            session,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )


def get_week_progress(
    user_id: int,
    *,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> WeekProgress:
    """Calculate progress for the user's current active plan."""

    factory = session_factory or get_session_factory()
    plan_data = get_active_plan_data(user_id, session_factory=factory)
    if plan_data is None:
        return WeekProgress(0, 0, 0, 0, 0.0)

    tasks = plan_data.tasks
    completed_tasks = sum(task.status == "completed" for task in tasks)
    active_date = today or date.today()
    logs = get_study_logs(
        user_id,
        start_date=active_date - timedelta(days=6),
        end_date=active_date,
        session_factory=factory,
    )
    return WeekProgress(
        total_tasks=len(tasks),
        completed_tasks=completed_tasks,
        planned_minutes=sum(task.planned_minutes for task in tasks),
        actual_minutes=sum(log.minutes for log in logs),
        completion_rate=completed_tasks / len(tasks) if tasks else 0.0,
    )
