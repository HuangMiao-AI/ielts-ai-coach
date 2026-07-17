"""Tests for task completion, cancellation, logs, and isolation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.scores import save_score_record
from ielts_ai_coach.services.tasks import (
    TaskUpdateError,
    cancel_task_completion,
    complete_task,
    get_study_logs,
    get_tasks_for_day,
)


def _prepare_student(
    username: str,
    session_factory: sessionmaker[Session],
    today: date,
) -> int:
    """Create a complete student with an active plan."""

    user_id = register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname=username,
        grade="高一",
        target_overall=7.0,
        exam_date=today + timedelta(days=80),
        daily_study_minutes=60,
        today=today,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.0,
            "reading": 6.0,
            "writing": 5.5,
            "speaking": 5.5,
        },
        session_factory=session_factory,
    )
    generate_plan(user_id, today=today, session_factory=session_factory)
    return user_id


def test_task_completion_and_cancellation_update_study_log(
    session_factory: sessionmaker[Session],
) -> None:
    """Completing and cancelling a task must update its study log."""

    today = date(2026, 7, 16)
    user_id = _prepare_student("TaskOwner", session_factory, today)
    task = get_tasks_for_day(
        user_id, task_date=today, session_factory=session_factory
    )[0]

    completed_task = complete_task(
        user_id=user_id,
        task_id=task.id,
        actual_minutes=42,
        session_factory=session_factory,
    )
    logs = get_study_logs(
        user_id,
        start_date=today,
        end_date=today,
        session_factory=session_factory,
    )

    assert completed_task.status == "completed"
    assert completed_task.actual_minutes == 42
    assert len(logs) == 1
    assert logs[0].minutes == 42

    pending_task = cancel_task_completion(
        user_id=user_id,
        task_id=task.id,
        session_factory=session_factory,
    )
    assert pending_task.status == "pending"
    assert (
        get_study_logs(
            user_id,
            start_date=today,
            end_date=today,
            session_factory=session_factory,
        )
        == []
    )


def test_completion_defaults_actual_time_to_planned_minutes(
    session_factory: sessionmaker[Session],
) -> None:
    """One-click completion must use the task's planned time by default."""

    today = date(2026, 7, 16)
    user_id = _prepare_student("TaskDefaultTime", session_factory, today)
    task = get_tasks_for_day(
        user_id,
        task_date=today,
        session_factory=session_factory,
    )[0]

    completed_task = complete_task(
        user_id=user_id,
        task_id=task.id,
        session_factory=session_factory,
    )
    logs = get_study_logs(
        user_id,
        start_date=today,
        end_date=today,
        session_factory=session_factory,
    )

    assert completed_task.actual_minutes == task.planned_minutes
    assert logs[0].minutes == task.planned_minutes


def test_user_cannot_update_another_users_task(
    session_factory: sessionmaker[Session],
) -> None:
    """Task updates must require both task ID and owning user ID."""

    today = date(2026, 7, 16)
    owner_id = _prepare_student("TaskOwnerTwo", session_factory, today)
    other_id = _prepare_student("TaskOther", session_factory, today)
    owner_task = get_tasks_for_day(
        owner_id, task_date=today, session_factory=session_factory
    )[0]

    with pytest.raises(TaskUpdateError):
        complete_task(
            user_id=other_id,
            task_id=owner_task.id,
            actual_minutes=30,
            session_factory=session_factory,
        )

    assert get_tasks_for_day(
        owner_id, task_date=today, session_factory=session_factory
    )[0].status == "pending"
