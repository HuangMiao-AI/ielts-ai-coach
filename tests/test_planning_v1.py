"""Tests for deterministic planning rules and plan versioning."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.services.planning import (
    generate_plan,
    get_active_plan_data,
    get_plan_history,
)
from ielts_ai_coach.services.planning_rules import (
    build_plan_blueprint,
    determine_exam_phase,
)
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.scores import save_score_record


def _prepare_student(
    username: str,
    session_factory: sessionmaker[Session],
    today: date,
) -> int:
    """Create a complete student ready for plan generation."""

    user_id = register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname=username,
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=60),
        daily_study_minutes=95,
        today=today,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 6.5,
            "writing": 5.5,
            "speaking": 5.5,
        },
        session_factory=session_factory,
    )
    return user_id


def test_exam_phase_boundaries() -> None:
    """The three approved exam stages must use exact day boundaries."""

    today = date(2026, 7, 16)
    assert determine_exam_phase(today + timedelta(days=91), today) == "foundation"
    assert determine_exam_phase(today + timedelta(days=90), today) == "targeted"
    assert determine_exam_phase(today + timedelta(days=31), today) == "targeted"
    assert determine_exam_phase(today + timedelta(days=30), today) == "exam"


def test_each_plan_day_uses_exact_daily_minutes() -> None:
    """Every date must allocate exactly the configured study time."""

    today = date(2026, 7, 16)
    blueprint = build_plan_blueprint(
        scores={
            "listening": 7.0,
            "reading": 6.5,
            "writing": 5.5,
            "speaking": 5.5,
        },
        target_overall=7.0,
        exam_date=today + timedelta(days=120),
        daily_minutes=95,
        start_date=today,
    )
    minutes_by_date: dict[date, int] = defaultdict(int)
    minutes_by_subject: dict[str, int] = defaultdict(int)
    for task in blueprint.tasks:
        minutes_by_date[task.task_date] += task.planned_minutes
        minutes_by_subject[task.subject] += task.planned_minutes

    assert len(minutes_by_date) == 7
    assert set(minutes_by_date.values()) == {95}
    assert minutes_by_subject["writing"] > minutes_by_subject["listening"]
    assert minutes_by_subject["speaking"] > minutes_by_subject["reading"]


def test_regeneration_archives_old_plan_without_deleting_history(
    session_factory: sessionmaker[Session],
) -> None:
    """Only one plan may stay active while earlier versions remain."""

    today = date(2026, 7, 16)
    user_id = _prepare_student("PlanVersion", session_factory, today)

    first_plan = generate_plan(
        user_id, today=today, session_factory=session_factory
    )
    second_plan = generate_plan(
        user_id, today=today, session_factory=session_factory
    )
    active_plan = get_active_plan_data(
        user_id, session_factory=session_factory
    )
    history = get_plan_history(user_id, session_factory=session_factory)

    assert first_plan.plan.id != second_plan.plan.id
    assert active_plan.plan.id == second_plan.plan.id
    assert len(history) == 2
    assert sum(plan.status == "active" for plan in history) == 1
    assert sum(plan.status == "archived" for plan in history) == 1
