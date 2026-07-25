"""User-scoped internal task containers for the Reading library."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.models import PlanTask, StudyPlan


def get_library_plan(session: Session, user_id: int) -> StudyPlan | None:
    """Return the internal Reading-library container owned by a user."""

    statement = (
        select(StudyPlan)
        .where(
            StudyPlan.user_id == user_id,
            StudyPlan.status == "library",
            StudyPlan.phase == "library",
        )
        .order_by(StudyPlan.created_at.desc(), StudyPlan.id.desc())
        .limit(1)
    )
    return session.scalar(statement)


def create_library_plan(
    session: Session,
    *,
    user_id: int,
    active_date: date,
) -> StudyPlan:
    """Create an internal task container without affecting active plans."""

    plan = StudyPlan(
        user_id=user_id,
        start_date=active_date,
        end_date=active_date,
        phase="library",
        status="library",
    )
    session.add(plan)
    session.flush()
    return plan


def list_user_tasks_by_subject(
    session: Session,
    *,
    user_id: int,
    subject: str,
) -> list[PlanTask]:
    """Return user-owned subject tasks, including internal library tasks."""

    statement = (
        select(PlanTask)
        .join(StudyPlan, StudyPlan.id == PlanTask.plan_id)
        .where(
            PlanTask.user_id == user_id,
            PlanTask.subject == subject,
            StudyPlan.user_id == user_id,
        )
        .order_by(PlanTask.created_at.desc(), PlanTask.id.desc())
    )
    return list(session.scalars(statement))
