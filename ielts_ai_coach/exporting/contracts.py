"""Strict versioned contracts for allowlisted export data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from ielts_ai_coach.exporting.enums import (
    FeedbackMethod,
    FeedbackStatus,
    Skill,
    SourceEntity,
)


class StrictExportModel(BaseModel):
    """Reject implicit coercion, extra fields, and post-create mutation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class FeedbackDetail(StrictExportModel):
    """One privacy-filtered reading review detail."""

    question_id: str = Field(min_length=1, max_length=80)
    question_type: str = Field(min_length=1, max_length=80)
    result: Literal["correct", "incorrect"]
    explanation: str = Field(max_length=2000)
    evidence: str = Field(max_length=2000)


class ReadingSourceRecord(StrictExportModel):
    """Allowlisted source data for one immutable reading attempt."""

    source_record_id: int = Field(gt=0)
    submitted_at: datetime
    passage_id: str = Field(min_length=1, max_length=80)
    passage_version: str = Field(min_length=1, max_length=40)
    score: int = Field(ge=0)
    total_questions: int = Field(gt=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    incorrect_question_ids: tuple[str, ...]
    details: tuple[FeedbackDetail, ...]

    @field_validator("submitted_at")
    @classmethod
    def require_aware_submitted_at(cls, value: datetime) -> datetime:
        """Require a timestamp with a defined UTC offset."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("submitted_at must include timezone")
        return value


class WritingSourceRecord(StrictExportModel):
    """Allowlisted source data for one validated writing feedback row."""

    source_record_id: int = Field(gt=0)
    created_at: datetime
    test_type: str = Field(min_length=1, max_length=20)
    task_type: str = Field(min_length=1, max_length=20)
    word_count: int = Field(ge=0)
    task_response_or_achievement: float = Field(ge=0.0, le=9.0)
    coherence_and_cohesion: float = Field(ge=0.0, le=9.0)
    lexical_resource: float = Field(ge=0.0, le=9.0)
    grammatical_range_and_accuracy: float = Field(ge=0.0, le=9.0)
    estimated_overall: float = Field(ge=0.0, le=9.0)
    strengths: tuple[str, ...]
    main_issues: tuple[str, ...]
    actionable_suggestions: tuple[str, ...]
    rewrite_example: str = Field(max_length=1800)
    disclaimer: str = Field(max_length=300)
    provider: str = Field(max_length=30)
    model_name: str = Field(max_length=80)

    @field_validator("created_at")
    @classmethod
    def require_aware_created_at(cls, value: datetime) -> datetime:
        """Require a timestamp with a defined UTC offset."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include timezone")
        return value


class FeedbackExportRecord(StrictExportModel):
    """Version 1 shared input for every export adapter."""

    schema_version: Literal[1] = 1
    type: Literal["ai-coach-feedback"] = "ai-coach-feedback"
    source_system: Literal["ielts-ai-coach"] = "ielts-ai-coach"
    source_entity: SourceEntity
    source_record_id: int = Field(gt=0)
    session_date: date
    generated_at: datetime
    coach_version: str | None = None
    exporter_version: Literal["1.0.0"] = "1.0.0"
    skill: Skill
    feedback_method: FeedbackMethod
    provider: str | None = None
    model_name: str | None = None
    feedback_status: FeedbackStatus = FeedbackStatus.GENERATED
    overall_summary: tuple[str, ...]
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...]
    recommendations: tuple[str, ...]
    detailed_feedback: tuple[FeedbackDetail, ...] = ()
    rewrite_example: str | None = None
    disclaimer: str | None = None
    source_note: str | None = None
    test: bool = False
    tags: tuple[str, ...] = ("ielts", "ai-coach-feedback")

    @field_validator("generated_at")
    @classmethod
    def require_aware_generated_at(cls, value: datetime) -> datetime:
        """Reject ambiguous generated timestamps."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must include timezone")
        return value


class ExportUserSummary(StrictExportModel):
    """Minimum account information needed for an owner to choose user_id."""

    user_id: int = Field(gt=0)
    account_label: str = Field(min_length=1, max_length=24)
    has_profile: bool
    reading_count: int = Field(ge=0)
    writing_count: int = Field(ge=0)
    recent_activity_at: datetime | None = None
