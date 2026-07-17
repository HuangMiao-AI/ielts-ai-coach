"""Tests for student profile validation, CRUD, and isolation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.services.profiles import (
    ProfileValidationError,
    get_profile,
    save_profile,
)


def _create_user(
    username: str, session_factory: sessionmaker[Session]
) -> int:
    """Create a test user and return its ID."""

    return register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id


def test_profile_create_and_update_keeps_one_row(
    session_factory: sessionmaker[Session],
) -> None:
    """One user must have one profile that is updated in place."""

    user_id = _create_user("ProfileUser", session_factory)
    today = date(2026, 7, 16)
    first_profile = save_profile(
        user_id=user_id,
        nickname="小雅",
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=120),
        daily_study_minutes=90,
        today=today,
        session_factory=session_factory,
    )
    updated_profile = save_profile(
        user_id=user_id,
        nickname="小雅同学",
        grade="高三",
        target_overall=7.5,
        exam_date=today + timedelta(days=90),
        daily_study_minutes=120,
        today=today,
        session_factory=session_factory,
    )

    assert first_profile.id == updated_profile.id
    assert updated_profile.nickname == "小雅同学"
    assert get_profile(
        user_id, session_factory=session_factory
    ).daily_study_minutes == 120


def test_profile_validation_rejects_invalid_values(
    session_factory: sessionmaker[Session],
) -> None:
    """Invalid bands, dates, and study minutes must be rejected."""

    user_id = _create_user("InvalidProfile", session_factory)
    today = date(2026, 7, 16)
    base_values = {
        "user_id": user_id,
        "nickname": "学生",
        "grade": "高一",
        "target_overall": 7.0,
        "exam_date": today + timedelta(days=60),
        "daily_study_minutes": 60,
        "today": today,
        "session_factory": session_factory,
    }

    for overrides in (
        {"target_overall": 7.2},
        {"exam_date": today - timedelta(days=1)},
        {"daily_study_minutes": 5},
    ):
        with pytest.raises(ProfileValidationError):
            save_profile(**(base_values | overrides))


def test_profiles_are_isolated_by_user(
    session_factory: sessionmaker[Session],
) -> None:
    """A user lookup must never return another user's profile."""

    first_user_id = _create_user("ProfileOne", session_factory)
    second_user_id = _create_user("ProfileTwo", session_factory)
    today = date(2026, 7, 16)
    save_profile(
        user_id=first_user_id,
        nickname="用户一",
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=100),
        daily_study_minutes=90,
        today=today,
        session_factory=session_factory,
    )

    assert get_profile(
        first_user_id, session_factory=session_factory
    ).nickname == "用户一"
    assert get_profile(second_user_id, session_factory=session_factory) is None
