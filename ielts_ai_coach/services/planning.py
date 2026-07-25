"""Persistence orchestration for deterministic study plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.models import PlanTask, StudyPlan
from ielts_ai_coach.database.plan_repository import (
    archive_active_plans,
    create_plan,
    create_plan_task,
    get_active_plan,
    list_plan_tasks,
    list_plans,
    recent_completion_rate,
)
from ielts_ai_coach.services.planning_rules import (
    PlanGenerationError,
    build_plan_blueprint,
)
from ielts_ai_coach.services.learner_profiles import get_learner_profile


@dataclass(frozen=True)
class ActivePlanData:
    """An active plan and all user-owned tasks within it."""

    plan: StudyPlan
    tasks: tuple[PlanTask, ...]


def generate_plan(
    user_id: int,
    *,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> ActivePlanData:
    """Generate and persist one active plan for a user."""

    active_date = today or date.today()
    factory = session_factory or get_session_factory()
    profile = get_learner_profile(user_id, session_factory=factory)
    if profile is None or not profile.onboarding_completed:
        raise PlanGenerationError("profile_required")
    with session_scope(factory) as session:
        completion_rate = recent_completion_rate(
            session,
            user_id=user_id,
            start_date=active_date - timedelta(days=7),
            end_date=active_date - timedelta(days=1),
        )
        blueprint = build_plan_blueprint(
            scores={
                "listening": profile.current_listening_band,
                "reading": profile.current_reading_band,
                "writing": profile.current_writing_band,
                "speaking": profile.current_speaking_band,
            },
            target_overall=profile.target_overall_band,
            exam_date=profile.exam_date,
            daily_minutes=profile.daily_study_minutes,
            completion_rate=completion_rate,
            start_date=active_date,
        )
        archive_active_plans(session, user_id)
        plan = create_plan(
            session,
            user_id=user_id,
            start_date=blueprint.start_date,
            end_date=blueprint.end_date,
            phase=blueprint.phase,
        )
        tasks = tuple(
            create_plan_task(
                session,
                user_id=user_id,
                plan_id=plan.id,
                task_date=task.task_date,
                subject=task.subject,
                task_type=task.task_type,
                title=task.task_title,
                description=task.description,
                planned_minutes=task.planned_minutes,
                priority=task.priority,
            )
            for task in blueprint.tasks
        )
        return ActivePlanData(plan=plan, tasks=tasks)


def get_active_plan_data(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> ActivePlanData | None:
    """Return the active plan and tasks owned by a user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        plan = get_active_plan(session, user_id)
        if plan is None:
            return None
        tasks = list_plan_tasks(session, user_id=user_id, plan_id=plan.id)
        return ActivePlanData(plan=plan, tasks=tuple(tasks))


def get_plan_history(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> list[StudyPlan]:
    """Return plan versions owned by a user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return list_plans(session, user_id=user_id)
