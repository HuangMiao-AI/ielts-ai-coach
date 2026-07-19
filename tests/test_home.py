"""Tests for the real user-owned Home snapshot."""

from __future__ import annotations

from datetime import date, timedelta

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.services.home import (
    build_home_snapshot,
    calculate_streak,
)
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.scores import save_score_record
from ielts_ai_coach.services.tasks import complete_task


def _prepare_student(username, session_factory, today):
    """Create one profiled student with a generated plan."""

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
        daily_study_minutes=90,
        today=today,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 5.0,
            "writing": 6.0,
            "speaking": 6.5,
        },
        session_factory=session_factory,
    )
    plan = generate_plan(
        user_id,
        today=today,
        session_factory=session_factory,
    )
    return user_id, plan


def test_streak_counts_consecutive_days_ending_today_or_yesterday() -> None:
    """A current streak may remain alive before today's first study action."""

    today = date(2026, 7, 19)

    assert calculate_streak([], today=today) == 0
    assert calculate_streak(
        [today, today - timedelta(days=1), today - timedelta(days=2)],
        today=today,
    ) == 3
    assert calculate_streak(
        [today - timedelta(days=1), today - timedelta(days=2)],
        today=today,
    ) == 2
    assert calculate_streak(
        [today - timedelta(days=2)],
        today=today,
    ) == 0


def test_zero_data_snapshot_is_honest(
    session_factory,
) -> None:
    """A new user must receive actionable empty states, not fabricated values."""

    user_id = register_user(
        "EmptyHome",
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id

    snapshot = build_home_snapshot(
        user_id,
        today=date(2026, 7, 19),
        session_factory=session_factory,
    )

    assert snapshot.streak_days == 0
    assert snapshot.latest_reading is None
    assert snapshot.latest_writing is None
    assert snapshot.today_tasks == ()
    assert snapshot.recommended_route == "profile"


def test_home_activity_and_recommendation_are_user_isolated(
    session_factory,
) -> None:
    """A completed task and weak section must belong only to their owner."""

    today = date(2026, 7, 19)
    owner_id, owner_plan = _prepare_student(
        "HomeOwner",
        session_factory,
        today,
    )
    other_id, _ = _prepare_student("HomeOther", session_factory, today)
    owner_task = next(task for task in owner_plan.tasks if task.task_date == today)
    complete_task(
        user_id=owner_id,
        task_id=owner_task.id,
        session_factory=session_factory,
    )

    owner = build_home_snapshot(
        owner_id,
        today=today,
        session_factory=session_factory,
    )
    other = build_home_snapshot(
        other_id,
        today=today,
        session_factory=session_factory,
    )

    assert owner.streak_days == 1
    assert owner.completed_today == 1
    assert owner.weak_subjects == ("reading",)
    assert owner.recommended_route == "reading"
    assert other.streak_days == 0
    assert other.completed_today == 0
