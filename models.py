"""Shared data models used by the analysis, planning and database layers."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AnalysisResult:
    """A student's IELTS score analysis."""

    overall_band: float
    lowest_score: float
    lowest_subjects: tuple[str, ...]
    recommendations: dict[str, list[str]]


@dataclass(frozen=True)
class StudyRecord:
    """A normalized record returned from SQLite."""

    id: int
    student_name: str
    scores: dict[str, float]
    overall_band: float
    lowest_subjects: list[str]
    daily_minutes: int
    recommendations: dict[str, list[str]]
    study_plan: dict[str, Any]
    created_at: str
