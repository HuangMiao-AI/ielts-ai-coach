"""User-scoped persistence for student profiles and IELTS scores."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.models import ScoreRecord, StudentProfile


def get_profile(session: Session, user_id: int) -> StudentProfile | None:
    """Return the profile owned by a user."""

    statement = select(StudentProfile).where(StudentProfile.user_id == user_id)
    return session.scalar(statement)


def upsert_profile(
    session: Session,
    *,
    user_id: int,
    nickname: str,
    grade: str,
    target_overall: float,
    exam_date: date,
    daily_study_minutes: int,
) -> StudentProfile:
    """Create or update the single profile owned by a user."""

    profile = get_profile(session, user_id)
    if profile is None:
        profile = StudentProfile(user_id=user_id)
        session.add(profile)

    profile.nickname = nickname
    profile.grade = grade
    profile.target_overall = target_overall
    profile.exam_date = exam_date
    profile.daily_study_minutes = daily_study_minutes
    session.flush()
    return profile


def create_score_record(
    session: Session,
    *,
    user_id: int,
    listening: float,
    reading: float,
    writing: float,
    speaking: float,
    overall: float,
    note: str,
    recorded_at: datetime | None = None,
) -> ScoreRecord:
    """Create one score record owned by a user."""

    record = ScoreRecord(
        user_id=user_id,
        listening=listening,
        reading=reading,
        writing=writing,
        speaking=speaking,
        overall=overall,
        note=note,
    )
    if recorded_at is not None:
        record.recorded_at = recorded_at
    session.add(record)
    session.flush()
    return record


def get_score_record(
    session: Session, *, user_id: int, record_id: int
) -> ScoreRecord | None:
    """Return one score record only when it belongs to the user."""

    statement = select(ScoreRecord).where(
        ScoreRecord.id == record_id,
        ScoreRecord.user_id == user_id,
    )
    return session.scalar(statement)


def list_score_records(
    session: Session, *, user_id: int, limit: int = 100
) -> list[ScoreRecord]:
    """Return a user's score history from newest to oldest."""

    safe_limit = max(1, min(limit, 500))
    statement = (
        select(ScoreRecord)
        .where(ScoreRecord.user_id == user_id)
        .order_by(ScoreRecord.recorded_at.desc(), ScoreRecord.id.desc())
        .limit(safe_limit)
    )
    return list(session.scalars(statement))


def get_latest_score(session: Session, user_id: int) -> ScoreRecord | None:
    """Return the newest score record owned by a user."""

    records = list_score_records(session, user_id=user_id, limit=1)
    return records[0] if records else None
