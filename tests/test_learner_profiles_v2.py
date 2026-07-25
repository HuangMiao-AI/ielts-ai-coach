"""Behavior contracts for the additive learner profile V2."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import LearnerProfileV2
from ielts_ai_coach.services.learner_profiles import (
    LearnerProfileValidationError,
    get_learner_profile,
    save_learner_profile,
)
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.scores import save_score_record


def _user(session_factory, username: str) -> int:
    """Create one isolated test account."""

    return register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id


def _save(
    *,
    user_id: int,
    session_factory,
    reading: float | None = None,
    listening: float | None = None,
    writing: float | None = None,
    speaking: float | None = None,
):
    """Save one valid V2 profile with selectable optional bands."""

    return save_learner_profile(
        user_id=user_id,
        display_name="审计学生",
        current_grade="高二",
        exam_date=None,
        daily_study_minutes=75,
        target_overall_band=7.0,
        current_reading_band=reading,
        current_listening_band=listening,
        current_writing_band=writing,
        current_speaking_band=speaking,
        onboarding_completed=True,
        session_factory=session_factory,
    )


def test_v2_profile_accepts_all_missing_optional_bands_and_date(
    session_factory,
) -> None:
    """Missing evidence is persisted as None rather than a fake band/date."""

    user_id = _user(session_factory, "EmptyBaseline")

    saved = _save(user_id=user_id, session_factory=session_factory)
    loaded = get_learner_profile(
        user_id,
        session_factory=session_factory,
    )

    assert loaded == saved
    assert loaded is not None
    assert loaded.source == "v2"
    assert loaded.exam_date is None
    assert loaded.current_reading_band is None
    assert loaded.current_listening_band is None
    assert loaded.current_writing_band is None
    assert loaded.current_speaking_band is None


def test_v2_profile_preserves_zero_and_partial_bands(
    session_factory,
) -> None:
    """Zero remains measured data while omitted skills stay missing."""

    user_id = _user(session_factory, "PartialBaseline")

    loaded = _save(
        user_id=user_id,
        session_factory=session_factory,
        reading=0.0,
        writing=5.5,
    )

    assert loaded.current_reading_band == 0.0
    assert loaded.current_writing_band == 5.5
    assert loaded.current_listening_band is None
    assert loaded.current_speaking_band is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_reading_band", 6.25),
        ("current_listening_band", -0.5),
        ("current_writing_band", 9.5),
        ("current_speaking_band", 7.25),
        ("target_overall_band", 6.25),
    ],
)
def test_v2_profile_rejects_invalid_band_values(
    session_factory,
    field: str,
    value: float,
) -> None:
    """Every supplied band must be a real 0–9 half band."""

    user_id = _user(session_factory, f"Invalid{field[-7:]}")
    values = {
        "user_id": user_id,
        "display_name": "无效分数",
        "current_grade": "高二",
        "exam_date": None,
        "daily_study_minutes": 60,
        "target_overall_band": 7.0,
        "current_reading_band": None,
        "current_listening_band": None,
        "current_writing_band": None,
        "current_speaking_band": None,
        "onboarding_completed": True,
        "session_factory": session_factory,
    }
    values[field] = value

    with pytest.raises(LearnerProfileValidationError, match="invalid_band"):
        save_learner_profile(**values)


def test_v2_profile_queries_are_isolated_by_user(session_factory) -> None:
    """One user's V2 row is never returned for another user."""

    owner_id = _user(session_factory, "ProfileOwner")
    other_id = _user(session_factory, "ProfileOther")
    _save(
        user_id=owner_id,
        session_factory=session_factory,
        reading=8.5,
    )

    assert get_learner_profile(
        other_id,
        session_factory=session_factory,
    ) is None


def test_legacy_profile_reads_without_backfill_or_fake_scores(
    session_factory,
) -> None:
    """A legacy profile is adapted on read without creating V2 data."""

    user_id = _user(session_factory, "LegacyNoScore")
    exam_date = date.today() + timedelta(days=90)
    save_profile(
        user_id=user_id,
        nickname="旧用户",
        grade="大学",
        target_overall=7.5,
        exam_date=exam_date,
        daily_study_minutes=90,
        session_factory=session_factory,
    )

    loaded = get_learner_profile(
        user_id,
        session_factory=session_factory,
    )

    assert loaded is not None
    assert loaded.source == "legacy"
    assert loaded.display_name == "旧用户"
    assert loaded.exam_date == exam_date
    assert loaded.current_reading_band is None
    assert loaded.current_listening_band is None
    assert loaded.current_writing_band is None
    assert loaded.current_speaking_band is None
    with session_factory() as session:
        count = session.scalar(select(func.count(LearnerProfileV2.id)))
    assert count == 0


def test_legacy_profile_uses_only_a_real_latest_score_record(
    session_factory,
) -> None:
    """Existing complete historical scores remain visible compatibility data."""

    user_id = _user(session_factory, "LegacyRealScore")
    save_profile(
        user_id=user_id,
        nickname="有成绩旧用户",
        grade="高三",
        target_overall=7.0,
        exam_date=date.today() + timedelta(days=60),
        daily_study_minutes=60,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 6.0,
            "writing": 5.5,
            "speaking": 6.0,
        },
        session_factory=session_factory,
    )

    loaded = get_learner_profile(
        user_id,
        session_factory=session_factory,
    )

    assert loaded is not None
    assert loaded.source == "legacy"
    assert loaded.current_listening_band == 6.5
    assert loaded.current_reading_band == 6.0
    assert loaded.current_writing_band == 5.5
    assert loaded.current_speaking_band == 6.0


def test_v2_profile_takes_priority_over_legacy_profile_and_score(
    session_factory,
) -> None:
    """An explicit V2 save becomes the sole current-profile source."""

    user_id = _user(session_factory, "V2Priority")
    save_profile(
        user_id=user_id,
        nickname="旧昵称",
        grade="高一",
        target_overall=6.5,
        exam_date=date.today() + timedelta(days=45),
        daily_study_minutes=45,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 8.0,
            "reading": 8.0,
            "writing": 8.0,
            "speaking": 8.0,
        },
        session_factory=session_factory,
    )
    _save(
        user_id=user_id,
        session_factory=session_factory,
        reading=6.5,
    )

    loaded = get_learner_profile(
        user_id,
        session_factory=session_factory,
    )

    assert loaded is not None
    assert loaded.source == "v2"
    assert loaded.display_name == "审计学生"
    assert loaded.current_reading_band == 6.5
    assert loaded.current_listening_band is None


def test_active_legacy_edit_creates_exactly_one_v2_row(
    session_factory,
) -> None:
    """Only an explicit save creates the compatibility user's V2 row."""

    user_id = _user(session_factory, "LegacyEdit")
    save_profile(
        user_id=user_id,
        nickname="旧资料",
        grade="高二",
        target_overall=7.0,
        exam_date=date.today() + timedelta(days=100),
        daily_study_minutes=75,
        session_factory=session_factory,
    )

    _save(user_id=user_id, session_factory=session_factory, speaking=6.0)
    _save(user_id=user_id, session_factory=session_factory, speaking=6.5)

    with session_factory() as session:
        count = session.scalar(
            select(func.count(LearnerProfileV2.id)).where(
                LearnerProfileV2.user_id == user_id
            )
        )
    assert count == 1

