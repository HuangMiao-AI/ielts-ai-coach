"""Pure deterministic weakness analysis for aggregated learning evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ielts_ai_coach.services.analytics import AnalyticsResult, ReadingAnalytics


Severity = Literal["low", "medium", "high"]

_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
_READING_TYPE_LABELS = {
    "matching_heading": "Matching Heading",
    "multiple_choice": "Multiple Choice",
    "true_false_not_given": "True/False/Not Given",
}
_WRITING_WEAKNESSES = {
    "task_achievement": "Task Achievement improvement needed",
    "coherence": "Coherence improvement needed",
    "vocabulary": "Vocabulary improvement needed",
    "grammar": "Grammar improvement needed",
}


@dataclass(frozen=True)
class Weakness:
    """One evidence-backed skill weakness for learning guidance."""

    skill: str
    weakness: str
    severity: Severity
    evidence: str
    recommendation: str


def _reading_severity(accuracy: float) -> Severity | None:
    """Return the approved severity for submitted Reading accuracy."""

    if accuracy < 0.5:
        return "high"
    if accuracy < 0.6:
        return "medium"
    if accuracy < 0.7:
        return "low"
    return None


def _writing_severity(gap: float) -> Severity | None:
    """Return the approved severity for a Writing dimension target gap."""

    if gap >= 1.5:
        return "high"
    if gap >= 1.0:
        return "medium"
    if gap > 0:
        return "low"
    return None


def _question_type_label(question_type: str) -> str:
    """Format a stored Reading question type without exposing answer data."""

    return _READING_TYPE_LABELS.get(question_type, question_type)


def _percentage(accuracy: float) -> str:
    """Format an accuracy percentage without unnecessary trailing zeros."""

    return f"{accuracy * 100:.1f}".rstrip("0").rstrip(".") + "%"


def _reading_weakness(reading: ReadingAnalytics) -> Weakness | None:
    """Build one Reading weakness only when submitted evidence is sufficient."""

    if reading.accuracy is None or reading.total <= 0:
        return None
    severity = _reading_severity(reading.accuracy)
    if severity is None:
        return None

    labels = tuple(_question_type_label(name) for name in reading.frequent_error_types)
    type_description = " and ".join(labels)
    weakness = (
        f"Reading {type_description} accuracy needs improvement"
        if type_description
        else "Reading accuracy needs improvement"
    )
    recommendation = (
        f"Practise {type_description} question types and review the error pattern."
        if type_description
        else "Practise submitted Reading questions and review the error pattern."
    )
    error_counts = ", ".join(
        f"{question_type}={count}"
        for question_type, count in reading.error_counts
    ) or "none"
    return Weakness(
        skill="reading",
        weakness=weakness,
        severity=severity,
        evidence=(
            f"Submitted Reading: {reading.correct}/{reading.total} correct "
            f"({_percentage(reading.accuracy)}); errors: {error_counts}."
        ),
        recommendation=recommendation,
    )


def _writing_weaknesses(analytics: AnalyticsResult) -> tuple[Weakness, ...]:
    """Build weaknesses from latest Writing dimensions and the target band."""

    if analytics.target_band is None:
        return ()

    weaknesses: list[Weakness] = []
    for dimension in analytics.writing.dimensions:
        weakness_name = _WRITING_WEAKNESSES.get(dimension.name)
        if weakness_name is None or dimension.latest_band is None:
            continue
        gap = analytics.target_band - dimension.latest_band
        severity = _writing_severity(gap)
        if severity is None:
            continue
        weaknesses.append(
            Weakness(
                skill="writing",
                weakness=weakness_name,
                severity=severity,
                evidence=(
                    f"{dimension.name} band {dimension.latest_band:.1f}; "
                    f"target {analytics.target_band:.1f}; gap {gap:.1f}."
                ),
                recommendation=(
                    f"Prioritize targeted {dimension.name} practice before "
                    "the next Writing feedback submission."
                ),
            )
        )
    return tuple(weaknesses)


def analyze_weaknesses(analytics: AnalyticsResult) -> tuple[Weakness, ...]:
    """Return deterministically ordered Reading and Writing weaknesses only."""

    weaknesses = list(_writing_weaknesses(analytics))
    reading_weakness = _reading_weakness(analytics.reading)
    if reading_weakness is not None:
        weaknesses.append(reading_weakness)
    return tuple(
        sorted(
            weaknesses,
            key=lambda item: (
                _SEVERITY_RANK[item.severity],
                item.skill,
                item.weakness,
            ),
        )
    )
