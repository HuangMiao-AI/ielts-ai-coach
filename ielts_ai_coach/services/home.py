"""Read-only user-scoped aggregation for the authenticated Home page."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import get_session_factory
from ielts_ai_coach.database.models import Essay, PlanTask
from ielts_ai_coach.services.planning import get_active_plan_data
from ielts_ai_coach.services.profiles import get_profile
from ielts_ai_coach.services.reading_practice import (
    ReadingHistoryItem,
    list_reading_history,
)
from ielts_ai_coach.services.scoring import analyze_scores
from ielts_ai_coach.services.scores import get_latest_score
from ielts_ai_coach.services.tasks import get_study_logs
from ielts_ai_coach.services.writing import get_essay_history


@dataclass(frozen=True)
class HomeSnapshot:
    """All real data needed to render one user's Home experience."""

    streak_days: int
    latest_reading: ReadingHistoryItem | None
    latest_writing: Essay | None
    weak_subjects: tuple[str, ...]
    today_tasks: tuple[PlanTask, ...]
    plan_preview: tuple[PlanTask, ...]
    completed_today: int
    recent_activity: tuple[str, ...]
    recommended_route: str


def calculate_streak(
    study_dates: list[date] | tuple[date, ...],
    *,
    today: date,
) -> int:
    """Count consecutive study dates ending today or yesterday."""

    unique_dates = set(study_dates)
    if today in unique_dates:
        cursor = today
    elif today - timedelta(days=1) in unique_dates:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in unique_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _recommend_route(
    *,
    has_profile: bool,
    has_score: bool,
    has_plan: bool,
    weak_subjects: tuple[str, ...],
    today_tasks: tuple[PlanTask, ...],
) -> str:
    """Choose one deterministic next action from real account state."""

    if not has_profile:
        return "profile"
    if not has_score:
        return "scores"
    if not has_plan:
        return "plan"
    pending_subjects = {
        task.subject for task in today_tasks if task.status != "completed"
    }
    for subject in weak_subjects:
        if subject in pending_subjects or subject in {
            "reading",
            "listening",
            "writing",
            "speaking",
        }:
            return subject
    return "today" if pending_subjects else "history"


def build_home_snapshot(
    user_id: int,
    *,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> HomeSnapshot:
    """Aggregate existing user-owned records without creating new data."""

    active_date = today or date.today()
    factory = session_factory or get_session_factory()
    profile = get_profile(user_id, session_factory=factory)
    score = get_latest_score(user_id, session_factory=factory)
    plan = get_active_plan_data(user_id, session_factory=factory)
    logs = get_study_logs(
        user_id,
        start_date=active_date - timedelta(days=89),
        end_date=active_date,
        session_factory=factory,
    )
    reading_history = list_reading_history(
        user_id,
        limit=1,
        session_factory=factory,
    )
    essays = get_essay_history(user_id, session_factory=factory)
    tasks = tuple(plan.tasks) if plan else ()
    today_tasks = tuple(
        task for task in tasks if task.task_date == active_date
    )
    plan_preview = tuple(
        task
        for task in tasks
        if task.task_date >= active_date and task.status != "completed"
    )[:4]
    weak_subjects: tuple[str, ...] = ()
    if score is not None and profile is not None:
        diagnosis = analyze_scores(
            {
                "listening": score.listening,
                "reading": score.reading,
                "writing": score.writing,
                "speaking": score.speaking,
            },
            profile.target_overall,
        )
        weak_subjects = diagnosis.lowest_subjects
    activity = tuple(
        f"{log.study_date.isoformat()} · 完成 {log.minutes} 分钟"
        for log in reversed(logs[-5:])
    )
    return HomeSnapshot(
        streak_days=calculate_streak(
            [log.study_date for log in logs],
            today=active_date,
        ),
        latest_reading=reading_history[0] if reading_history else None,
        latest_writing=essays[0] if essays else None,
        weak_subjects=weak_subjects,
        today_tasks=today_tasks,
        plan_preview=plan_preview,
        completed_today=sum(
            task.status == "completed" for task in today_tasks
        ),
        recent_activity=activity,
        recommended_route=_recommend_route(
            has_profile=profile is not None,
            has_score=score is not None,
            has_plan=plan is not None,
            weak_subjects=weak_subjects,
            today_tasks=today_tasks,
        ),
    )
