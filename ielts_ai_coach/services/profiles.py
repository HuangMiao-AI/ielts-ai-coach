"""Validation and orchestration for student profiles."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.account_repository import (
    get_profile as repository_get_profile,
    upsert_profile,
)
from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.models import StudentProfile


GRADE_OPTIONS = (
    "初三",
    "高一",
    "高二",
    "高三",
    "大学",
    "大学申请阶段",
    "其他",
)
MIN_DAILY_MINUTES = 15
MAX_DAILY_MINUTES = 480
MAX_EXAM_DATE_YEARS = 3


class ProfileValidationError(ValueError):
    """Raised when profile data does not satisfy V1 rules."""


class ProfilePersistenceError(RuntimeError):
    """Raised when a validated profile cannot be persisted."""


def is_valid_ielts_band(value: float) -> bool:
    """Return whether a value is a valid IELTS half-band from 0 to 9."""

    return 0.0 <= value <= 9.0 and abs(value * 2 - round(value * 2)) < 1e-9


def validate_profile(
    *,
    nickname: str,
    grade: str,
    target_overall: float,
    exam_date: date,
    daily_study_minutes: int,
    today: date | None = None,
) -> None:
    """Validate all student profile fields."""

    cleaned_nickname = nickname.strip()
    if not 1 <= len(cleaned_nickname) <= 40:
        raise ProfileValidationError("invalid_nickname")
    if grade not in GRADE_OPTIONS:
        raise ProfileValidationError("invalid_grade")
    if not is_valid_ielts_band(target_overall):
        raise ProfileValidationError("invalid_target")
    active_date = today or date.today()
    if exam_date < active_date:
        raise ProfileValidationError("exam_in_past")
    if exam_date > active_date + timedelta(days=366 * MAX_EXAM_DATE_YEARS):
        raise ProfileValidationError("exam_too_far")
    if not MIN_DAILY_MINUTES <= daily_study_minutes <= MAX_DAILY_MINUTES:
        raise ProfileValidationError("invalid_minutes")


def save_profile(
    *,
    user_id: int,
    nickname: str,
    grade: str,
    target_overall: float,
    exam_date: date,
    daily_study_minutes: int,
    session_factory: sessionmaker[Session] | None = None,
    today: date | None = None,
) -> StudentProfile:
    """Validate and persist the single profile owned by a user."""

    validate_profile(
        nickname=nickname,
        grade=grade,
        target_overall=target_overall,
        exam_date=exam_date,
        daily_study_minutes=daily_study_minutes,
        today=today,
    )
    factory = session_factory or get_session_factory()
    try:
        with session_scope(factory) as session:
            return upsert_profile(
                session,
                user_id=user_id,
                nickname=nickname.strip(),
                grade=grade,
                target_overall=float(target_overall),
                exam_date=exam_date,
                daily_study_minutes=int(daily_study_minutes),
            )
    except SQLAlchemyError as error:
        raise ProfilePersistenceError("database_error") from error


def get_profile(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> StudentProfile | None:
    """Return the profile owned by a user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return repository_get_profile(session, user_id)


def days_until_exam(profile: StudentProfile, today: date | None = None) -> int:
    """Return the non-negative number of days until a profile exam."""

    active_date = today or date.today()
    return max(0, (profile.exam_date - active_date).days)
