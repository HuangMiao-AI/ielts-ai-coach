"""User-scoped persistence for the additive learner profile V2."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.learner_profile_models import LearnerProfileV2


def get_learner_profile_v2(
    session: Session,
    user_id: int,
) -> LearnerProfileV2 | None:
    """Return a V2 learner profile only when it belongs to the user."""

    statement = select(LearnerProfileV2).where(
        LearnerProfileV2.user_id == user_id
    )
    return session.scalar(statement)


def upsert_learner_profile_v2(
    session: Session,
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
) -> LearnerProfileV2:
    """Create or update the single V2 row owned by one user."""

    profile = get_learner_profile_v2(session, user_id)
    if profile is None:
        profile = LearnerProfileV2(user_id=user_id)
        session.add(profile)
    profile.display_name = display_name
    profile.current_grade = current_grade
    profile.exam_date = exam_date
    profile.daily_study_minutes = daily_study_minutes
    profile.target_overall_band = target_overall_band
    profile.current_reading_band = current_reading_band
    profile.current_listening_band = current_listening_band
    profile.current_writing_band = current_writing_band
    profile.current_speaking_band = current_speaking_band
    profile.onboarding_completed = onboarding_completed
    session.flush()
    return profile

