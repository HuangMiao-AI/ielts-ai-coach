"""AI conversation, quota, essay, and feedback database models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from ielts_ai_coach.database.base import Base, utc_now


class CoachMessage(Base):
    """One user or assistant message in a student's coach history."""

    __tablename__ = "coach_messages"
    __table_args__ = (
        Index("ix_coach_messages_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    model_name: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AIUsageDaily(Base):
    """Successful daily AI usage counters for one user."""

    __tablename__ = "ai_usage_daily"
    __table_args__ = (
        UniqueConstraint("user_id", "usage_date", name="uq_ai_usage_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    coach_success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    writing_success_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class Essay(Base):
    """An IELTS essay submission owned by one user."""

    __tablename__ = "essays"
    __table_args__ = (
        Index("ix_essays_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    test_type: Mapped[str] = mapped_column(String(20), nullable=False)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    last_error: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class WritingFeedback(Base):
    """Validated structured AI feedback for one essay attempt."""

    __tablename__ = "writing_feedback"
    __table_args__ = (
        Index("ix_writing_feedback_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    essay_id: Mapped[int] = mapped_column(
        ForeignKey("essays.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_response_or_achievement: Mapped[float] = mapped_column(
        nullable=False
    )
    coherence_and_cohesion: Mapped[float] = mapped_column(nullable=False)
    lexical_resource: Mapped[float] = mapped_column(nullable=False)
    grammatical_range_and_accuracy: Mapped[float] = mapped_column(nullable=False)
    estimated_overall: Mapped[float] = mapped_column(nullable=False)
    strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    main_issues: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    actionable_suggestions: Mapped[list[str]] = mapped_column(
        JSON, nullable=False
    )
    rewrite_example: Mapped[str] = mapped_column(Text, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
