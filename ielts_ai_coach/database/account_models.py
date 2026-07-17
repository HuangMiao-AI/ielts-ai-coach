"""Account, profile, and IELTS score database models."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from ielts_ai_coach.database.base import Base, utc_now


class User(Base):
    """A student account with a securely hashed password."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(24), nullable=False)
    username_normalized: Mapped[str] = mapped_column(
        String(24), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class StudentProfile(Base):
    """One active IELTS study profile owned by one user."""

    __tablename__ = "student_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_student_profiles_user_id"),
        CheckConstraint(
            "target_overall >= 0 AND target_overall <= 9",
            name="ck_profile_target_band",
        ),
        CheckConstraint(
            "daily_study_minutes >= 15 AND daily_study_minutes <= 480",
            name="ck_profile_daily_minutes",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nickname: Mapped[str] = mapped_column(String(40), nullable=False)
    grade: Mapped[str] = mapped_column(String(30), nullable=False)
    target_overall: Mapped[float] = mapped_column(Float, nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False)
    daily_study_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ScoreRecord(Base):
    """One historical set of IELTS section scores owned by a user."""

    __tablename__ = "score_records"
    __table_args__ = (
        CheckConstraint(
            "listening >= 0 AND listening <= 9 "
            "AND reading >= 0 AND reading <= 9 "
            "AND writing >= 0 AND writing <= 9 "
            "AND speaking >= 0 AND speaking <= 9 "
            "AND overall >= 0 AND overall <= 9",
            name="ck_score_band_ranges",
        ),
        Index("ix_score_records_user_recorded", "user_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    listening: Mapped[float] = mapped_column(Float, nullable=False)
    reading: Mapped[float] = mapped_column(Float, nullable=False)
    writing: Mapped[float] = mapped_column(Float, nullable=False)
    speaking: Mapped[float] = mapped_column(Float, nullable=False)
    overall: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    note: Mapped[str] = mapped_column(String(300), nullable=False, default="")
