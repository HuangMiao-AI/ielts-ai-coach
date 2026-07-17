"""Pydantic schemas for structured AI output."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


BandScore = Annotated[float, Field(ge=0.0, le=9.0)]


class WritingFeedbackSchema(BaseModel):
    """Validated Level 2 IELTS writing feedback."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task_response_or_achievement: BandScore
    coherence_and_cohesion: BandScore
    lexical_resource: BandScore
    grammatical_range_and_accuracy: BandScore
    estimated_overall: BandScore
    strengths: list[str] = Field(min_length=1, max_length=8)
    main_issues: list[str] = Field(min_length=1, max_length=8)
    actionable_suggestions: list[str] = Field(min_length=1, max_length=10)
    rewrite_example: str = Field(min_length=20, max_length=1800)
    disclaimer: str = Field(min_length=10, max_length=300)

    @field_validator(
        "task_response_or_achievement",
        "coherence_and_cohesion",
        "lexical_resource",
        "grammatical_range_and_accuracy",
        "estimated_overall",
    )
    @classmethod
    def validate_half_band(cls, value: float) -> float:
        """Require all estimated bands to use half-band increments."""

        if abs(value * 2 - round(value * 2)) > 1e-9:
            raise ValueError("Band scores must use half-band increments.")
        return float(value)

    @field_validator("strengths", "main_issues", "actionable_suggestions")
    @classmethod
    def validate_list_items(cls, values: list[str]) -> list[str]:
        """Reject empty or excessively long feedback list items."""

        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 500 for value in cleaned):
            raise ValueError("Feedback list items must be concise.")
        return cleaned
