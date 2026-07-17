"""User-scoped daily AI usage persistence."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.models import AIUsageDaily


def get_daily_usage(
    session: Session, *, user_id: int, usage_date: date
) -> AIUsageDaily | None:
    """Return one user's usage row for one date."""

    statement = select(AIUsageDaily).where(
        AIUsageDaily.user_id == user_id,
        AIUsageDaily.usage_date == usage_date,
    )
    return session.scalar(statement)


def get_or_create_daily_usage(
    session: Session, *, user_id: int, usage_date: date
) -> AIUsageDaily:
    """Return or create one user's daily usage row."""

    usage = get_daily_usage(session, user_id=user_id, usage_date=usage_date)
    if usage is None:
        usage = AIUsageDaily(user_id=user_id, usage_date=usage_date)
        session.add(usage)
        session.flush()
    return usage


def increment_successful_usage(
    session: Session,
    *,
    user_id: int,
    usage_date: date,
    category: str,
) -> AIUsageDaily:
    """Increment a successful coach or writing call for one user."""

    usage = get_or_create_daily_usage(
        session, user_id=user_id, usage_date=usage_date
    )
    if category == "coach":
        usage.coach_success_count += 1
    elif category == "writing":
        usage.writing_success_count += 1
    else:
        raise ValueError("Unknown AI usage category.")
    session.flush()
    return usage
