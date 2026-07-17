"""User-scoped persistence for plans, tasks, and study logs."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.base import utc_now
from ielts_ai_coach.database.models import PlanTask, StudyLog, StudyPlan


def archive_active_plans(session: Session, user_id: int) -> int:
    """Archive all active plans owned by a user and return the count."""

    statement = select(StudyPlan).where(
        StudyPlan.user_id == user_id,
        StudyPlan.status == "active",
    )
    plans = list(session.scalars(statement))
    archived_at = utc_now()
    for plan in plans:
        plan.status = "archived"
        plan.archived_at = archived_at
    return len(plans)


def create_plan(
    session: Session,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
    phase: str,
) -> StudyPlan:
    """Create one active seven-day plan owned by a user."""

    plan = StudyPlan(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        phase=phase,
        status="active",
    )
    session.add(plan)
    session.flush()
    return plan


def create_plan_task(
    session: Session,
    *,
    user_id: int,
    plan_id: int,
    task_date: date,
    subject: str,
    task_type: str,
    title: str,
    description: str,
    planned_minutes: int,
    priority: int,
) -> PlanTask:
    """Create one task owned by the same user as its plan."""

    task = PlanTask(
        user_id=user_id,
        plan_id=plan_id,
        task_date=task_date,
        subject=subject,
        task_type=task_type,
        title=title,
        description=description,
        planned_minutes=planned_minutes,
        priority=priority,
    )
    session.add(task)
    session.flush()
    return task


def get_active_plan(session: Session, user_id: int) -> StudyPlan | None:
    """Return the newest active plan owned by a user."""

    statement = (
        select(StudyPlan)
        .where(
            StudyPlan.user_id == user_id,
            StudyPlan.status == "active",
        )
        .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
        .limit(1)
    )
    return session.scalar(statement)


def list_plans(
    session: Session, *, user_id: int, limit: int = 20
) -> list[StudyPlan]:
    """Return a user's plan history from newest to oldest."""

    statement = (
        select(StudyPlan)
        .where(StudyPlan.user_id == user_id)
        .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
        .limit(max(1, min(limit, 100)))
    )
    return list(session.scalars(statement))


def list_plan_tasks(
    session: Session, *, user_id: int, plan_id: int
) -> list[PlanTask]:
    """Return tasks only when both task and plan belong to the user."""

    statement = (
        select(PlanTask)
        .join(StudyPlan, StudyPlan.id == PlanTask.plan_id)
        .where(
            PlanTask.user_id == user_id,
            PlanTask.plan_id == plan_id,
            StudyPlan.user_id == user_id,
        )
        .order_by(PlanTask.task_date, PlanTask.priority, PlanTask.id)
    )
    return list(session.scalars(statement))


def list_tasks_for_date(
    session: Session, *, user_id: int, task_date: date
) -> list[PlanTask]:
    """Return active-plan tasks owned by a user for one date."""

    statement = (
        select(PlanTask)
        .join(StudyPlan, StudyPlan.id == PlanTask.plan_id)
        .where(
            PlanTask.user_id == user_id,
            PlanTask.task_date == task_date,
            StudyPlan.user_id == user_id,
            StudyPlan.status == "active",
        )
        .order_by(PlanTask.priority, PlanTask.id)
    )
    return list(session.scalars(statement))


def get_task(
    session: Session, *, user_id: int, task_id: int
) -> PlanTask | None:
    """Return one task only when it belongs to the user."""

    statement = select(PlanTask).where(
        PlanTask.id == task_id,
        PlanTask.user_id == user_id,
    )
    return session.scalar(statement)


def set_task_completed(
    session: Session,
    *,
    user_id: int,
    task_id: int,
    actual_minutes: int | None,
) -> PlanTask | None:
    """Complete a task and use planned minutes when no override is given."""

    task = get_task(session, user_id=user_id, task_id=task_id)
    if task is None:
        return None

    recorded_minutes = (
        task.planned_minutes if actual_minutes is None else actual_minutes
    )
    task.status = "completed"
    task.actual_minutes = recorded_minutes
    task.completed_at = utc_now()
    log_statement = select(StudyLog).where(
        StudyLog.task_id == task_id,
        StudyLog.user_id == user_id,
    )
    study_log = session.scalar(log_statement)
    if study_log is None:
        study_log = StudyLog(
            user_id=user_id,
            task_id=task.id,
            study_date=task.task_date,
            minutes=recorded_minutes,
        )
        session.add(study_log)
    else:
        study_log.minutes = recorded_minutes
    session.flush()
    return task


def set_task_pending(
    session: Session, *, user_id: int, task_id: int
) -> PlanTask | None:
    """Cancel completion for a user-owned task and remove its active log."""

    task = get_task(session, user_id=user_id, task_id=task_id)
    if task is None:
        return None
    task.status = "pending"
    task.actual_minutes = None
    task.completed_at = None
    session.execute(
        delete(StudyLog).where(
            StudyLog.task_id == task_id,
            StudyLog.user_id == user_id,
        )
    )
    session.flush()
    return task


def list_study_logs(
    session: Session,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
) -> list[StudyLog]:
    """Return a user's study logs within an inclusive date range."""

    statement = (
        select(StudyLog)
        .where(
            StudyLog.user_id == user_id,
            StudyLog.study_date >= start_date,
            StudyLog.study_date <= end_date,
        )
        .order_by(StudyLog.study_date, StudyLog.id)
    )
    return list(session.scalars(statement))


def recent_completion_rate(
    session: Session,
    *,
    user_id: int,
    start_date: date,
    end_date: date,
) -> float:
    """Return the completion rate for user-owned tasks in a date range."""

    total_statement = select(func.count(PlanTask.id)).where(
        PlanTask.user_id == user_id,
        PlanTask.task_date >= start_date,
        PlanTask.task_date <= end_date,
    )
    completed_statement = select(func.count(PlanTask.id)).where(
        PlanTask.user_id == user_id,
        PlanTask.task_date >= start_date,
        PlanTask.task_date <= end_date,
        PlanTask.status == "completed",
    )
    total = int(session.scalar(total_statement) or 0)
    completed = int(session.scalar(completed_statement) or 0)
    return completed / total if total else 1.0
