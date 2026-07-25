"""Additive V2 learner profile with honest optional baseline evidence."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from ielts_ai_coach.database.base import Base, utc_now


def _optional_half_band_check(column: str) -> str:
    """Return a SQLite-compatible nullable half-band check expression."""

    return (
        f"{column} IS NULL OR ("
        f"{column} >= 0 AND {column} <= 9 AND "
        f"{column} * 2 = CAST({column} * 2 AS INTEGER))"
    )


class LearnerProfileV2(Base):
    """One explicit onboarding/profile record owned by one user."""

    __tablename__ = "learner_profiles_v2"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_learner_profiles_v2_user_id"),
        CheckConstraint(
            "daily_study_minutes >= 15 AND daily_study_minutes <= 480",
            name="ck_learner_profiles_v2_daily_minutes",
        ),
        CheckConstraint(
            "target_overall_band >= 0 AND target_overall_band <= 9 AND "
            "target_overall_band * 2 = "
            "CAST(target_overall_band * 2 AS INTEGER)",
            name="ck_learner_profiles_v2_target_band",
        ),
        CheckConstraint(
            _optional_half_band_check("current_reading_band"),
            name="ck_learner_profiles_v2_reading_band",
        ),
        CheckConstraint(
            _optional_half_band_check("current_listening_band"),
            name="ck_learner_profiles_v2_listening_band",
        ),
        CheckConstraint(
            _optional_half_band_check("current_writing_band"),
            name="ck_learner_profiles_v2_writing_band",
        ),
        CheckConstraint(
            _optional_half_band_check("current_speaking_band"),
            name="ck_learner_profiles_v2_speaking_band",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(40), nullable=False)
    current_grade: Mapped[str] = mapped_column(String(30), nullable=False)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    target_overall_band: Mapped[float] = mapped_column(Float, nullable=False)
    current_reading_band: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    current_listening_band: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    current_writing_band: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    current_speaking_band: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

