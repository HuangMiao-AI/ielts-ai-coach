"""Persisted user submissions for deterministic reading practice."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ielts_ai_coach.database.base import Base, utc_now


class TaskQuestionAttempt(Base):
    """One immutable scored submission for a user-owned plan task."""

    __tablename__ = "task_question_attempts"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_task_question_attempts_task_id"),
        Index(
            "ix_task_question_attempts_user_submitted",
            "user_id",
            "submitted_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("plan_tasks.id", ondelete="CASCADE"), nullable=False
    )
    passage_id: Mapped[str] = mapped_column(String(40), nullable=False)
    passage_version: Mapped[str] = mapped_column(String(20), nullable=False)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    results_json: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    incorrect_question_ids_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
