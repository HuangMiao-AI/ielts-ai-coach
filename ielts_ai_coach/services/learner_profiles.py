"""Validation and compatibility reads for learner profile V2."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.account_repository import (
    get_latest_score,
    get_profile,
)
from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.learner_profile_models import LearnerProfileV2
from ielts_ai_coach.database.learner_profile_repository import (
    get_learner_profile_v2,
    upsert_learner_profile_v2,
)
from ielts_ai_coach.services.profiles import (
    GRADE_OPTIONS,
    MAX_DAILY_MINUTES,
    MAX_EXAM_DATE_YEARS,
    MIN_DAILY_MINUTES,
    is_valid_ielts_band,
)


class LearnerProfileValidationError(ValueError):
    """Raised when learner settings do not satisfy the V2 contract."""


@dataclass(frozen=True)
class LearnerProfileSnapshot:
    """One normalized profile from V2 or legacy compatibility data."""

    user_id: int
    display_name: str
    current_grade: str
    exam_date: date | None
    daily_study_minutes: int
    target_overall_band: float
    current_reading_band: float | None
    current_listening_band: float | None
    current_writing_band: float | None
    current_speaking_band: float | None
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime
    source: Literal["v2", "legacy"]

    def current_band(self, skill: str) -> float | None:
        """Return one optional baseline by canonical skill name."""

        fields = {
            "reading": self.current_reading_band,
            "listening": self.current_listening_band,
            "writing": self.current_writing_band,
            "speaking": self.current_speaking_band,
        }
        if skill not in fields:
            raise KeyError(skill)
        return fields[skill]


def _utc_timestamp(value: datetime) -> datetime:
    """Normalize SQLite-naive and in-memory-aware timestamps to UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _snapshot_from_v2(profile: LearnerProfileV2) -> LearnerProfileSnapshot:
    """Convert the V2 ORM row into an immutable service value."""

    return LearnerProfileSnapshot(
        user_id=profile.user_id,
        display_name=profile.display_name,
        current_grade=profile.current_grade,
        exam_date=profile.exam_date,
        daily_study_minutes=profile.daily_study_minutes,
        target_overall_band=profile.target_overall_band,
        current_reading_band=profile.current_reading_band,
        current_listening_band=profile.current_listening_band,
        current_writing_band=profile.current_writing_band,
        current_speaking_band=profile.current_speaking_band,
        onboarding_completed=profile.onboarding_completed,
        created_at=_utc_timestamp(profile.created_at),
        updated_at=_utc_timestamp(profile.updated_at),
        source="v2",
    )


def _validate_optional_band(value: float | None) -> None:
    """Reject every supplied value outside the IELTS half-band scale."""

    if value is not None and not is_valid_ielts_band(value):
        raise LearnerProfileValidationError("invalid_band")


def validate_learner_profile(
    *,
    display_name: str,
    current_grade: str,
    exam_date: date | None,
    daily_study_minutes: int,
    target_overall_band: float,
    current_reading_band: float | None,
    current_listening_band: float | None,
    current_writing_band: float | None,
    current_speaking_band: float | None,
    today: date | None = None,
) -> None:
    """Validate all explicit learner-profile inputs without defaults."""

    if not 1 <= len(display_name.strip()) <= 40:
        raise LearnerProfileValidationError("invalid_display_name")
    if current_grade not in GRADE_OPTIONS:
        raise LearnerProfileValidationError("invalid_grade")
    if not is_valid_ielts_band(target_overall_band):
        raise LearnerProfileValidationError("invalid_band")
    for value in (
        current_reading_band,
        current_listening_band,
        current_writing_band,
        current_speaking_band,
    ):
        _validate_optional_band(value)
    if not MIN_DAILY_MINUTES <= daily_study_minutes <= MAX_DAILY_MINUTES:
        raise LearnerProfileValidationError("invalid_minutes")
    active_date = today or date.today()
    if exam_date is not None and exam_date < active_date:
        raise LearnerProfileValidationError("exam_in_past")
    if (
        exam_date is not None
        and exam_date
        > active_date + timedelta(days=366 * MAX_EXAM_DATE_YEARS)
    ):
        raise LearnerProfileValidationError("exam_too_far")


def get_learner_profile(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> LearnerProfileSnapshot | None:
    """Resolve V2 first, then adapt owned legacy data without writing."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        v2_profile = get_learner_profile_v2(session, user_id)
        if v2_profile is not None:
            return _snapshot_from_v2(v2_profile)
        legacy = get_profile(session, user_id)
        if legacy is None:
            return None
        score = get_latest_score(session, user_id)
        return LearnerProfileSnapshot(
            user_id=user_id,
            display_name=legacy.nickname,
            current_grade=legacy.grade,
            exam_date=legacy.exam_date,
            daily_study_minutes=legacy.daily_study_minutes,
            target_overall_band=legacy.target_overall,
            current_reading_band=score.reading if score else None,
            current_listening_band=score.listening if score else None,
            current_writing_band=score.writing if score else None,
            current_speaking_band=score.speaking if score else None,
            onboarding_completed=True,
            created_at=_utc_timestamp(legacy.created_at),
            updated_at=_utc_timestamp(legacy.updated_at),
            source="legacy",
        )


def save_learner_profile(
    *,
    user_id: int,
    display_name: str,
    current_grade: str,
    exam_date: date | None,
    daily_study_minutes: int,
    target_overall_band: float,
    current_reading_band: float | None,
    current_listening_band: float | None,
    current_writing_band: float | None,
    current_speaking_band: float | None,
    onboarding_completed: bool,
    session_factory: sessionmaker[Session] | None = None,
    today: date | None = None,
) -> LearnerProfileSnapshot:
    """Validate and explicitly create or update one user-owned V2 row."""

    validate_learner_profile(
        display_name=display_name,
        current_grade=current_grade,
        exam_date=exam_date,
        daily_study_minutes=daily_study_minutes,
        target_overall_band=target_overall_band,
        current_reading_band=current_reading_band,
        current_listening_band=current_listening_band,
        current_writing_band=current_writing_band,
        current_speaking_band=current_speaking_band,
        today=today,
    )
    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        profile = upsert_learner_profile_v2(
            session,
            user_id=user_id,
            display_name=display_name.strip(),
            current_grade=current_grade,
            exam_date=exam_date,
            daily_study_minutes=int(daily_study_minutes),
            target_overall_band=float(target_overall_band),
            current_reading_band=current_reading_band,
            current_listening_band=current_listening_band,
            current_writing_band=current_writing_band,
            current_speaking_band=current_speaking_band,
            onboarding_completed=bool(onboarding_completed),
        )
        return _snapshot_from_v2(profile)
