"""Mock-only natural-language explanations for aggregate learning analytics."""

from __future__ import annotations

from dataclasses import dataclass

from ielts_ai_coach.ai.base import AIProvider, AIProviderError
from ielts_ai_coach.ai.mock import MockAIProvider
from ielts_ai_coach.services.analytics import AnalyticsResult
from ielts_ai_coach.services.recommendations import StudyRecommendation
from ielts_ai_coach.services.weakness_analyzer import Weakness


AI_ANALYSIS_DISCLAIMER = "以上分析仅用于学习规划，不是官方IELTS评分或诊断。"
_MAX_FIELD_LENGTH = 240
_MAX_PROMPT_LENGTH = 1_600
_READING_TYPE_LABELS = {
    "matching_heading": "Matching Heading",
    "multiple_choice": "Multiple Choice",
    "true_false_not_given": "True/False/Not Given",
}
_WRITING_DIMENSION_LABELS = {
    "task_achievement": "Task Achievement",
    "coherence": "Coherence",
    "vocabulary": "Vocabulary",
    "grammar": "Grammar",
}


class AIAnalysisError(ValueError):
    """A safe local explanation error identified by a stable code."""

    def __init__(self, code: str) -> None:
        """Store only the safe error code for callers and users."""

        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AIAnalysisExplanation:
    """One local-provider explanation and normalized provider metadata."""

    content: str
    provider: str
    model_name: str
    is_mock: bool


def _bounded(value: object, *, limit: int = _MAX_FIELD_LENGTH) -> str:
    """Return a compact prompt field without carrying unbounded payloads."""

    text = str(value).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _format_band(value: float) -> str:
    """Format a score without unnecessary trailing zeros."""

    return f"{value:.1f}".rstrip("0").rstrip(".")


def _band_summary(analytics: AnalyticsResult) -> str:
    """Describe only available current and target score measurements."""

    parts: list[str] = []
    if analytics.current_band is not None:
        parts.append(f"current band={_format_band(analytics.current_band)}")
    if analytics.target_band is not None:
        parts.append(f"target band={_format_band(analytics.target_band)}")
    return "; ".join(parts) or "No current or target band measurement is available."


def _reading_summary(analytics: AnalyticsResult) -> str:
    """Describe aggregate Reading evidence without question-level content."""

    reading = analytics.reading
    if reading.total <= 0 or reading.accuracy is None:
        return "No submitted Reading aggregate is available."
    error_types = ", ".join(
        _READING_TYPE_LABELS[question_type]
        for question_type in reading.frequent_error_types
        if question_type in _READING_TYPE_LABELS
    ) or "none recorded"
    accuracy = f"{reading.accuracy * 100:.1f}".rstrip("0").rstrip(".")
    return (
        f"Reading aggregate: {reading.correct}/{reading.total} correct; "
        f"accuracy={accuracy}%; frequent error types={error_types}."
    )


def _writing_summary(analytics: AnalyticsResult) -> str:
    """Describe the latest four approved Writing dimensions when available."""

    bands = [
        f"{label}={_format_band(dimension.latest_band)}"
        for dimension in analytics.writing.dimensions
        if (label := _WRITING_DIMENSION_LABELS.get(dimension.name)) is not None
        and dimension.latest_band is not None
    ]
    return (
        "Latest Writing dimension bands: " + "; ".join(bands) + "."
        if bands
        else "No latest Writing dimension bands are available."
    )


def _weakness_summary(weaknesses: tuple[Weakness, ...]) -> str:
    """Describe only the caller's highest-priority weakness and evidence."""

    if not weaknesses:
        return "No measured weakness is available."
    weakness = weaknesses[0]
    return (
        f"Highest-priority weakness: {_bounded(weakness.weakness)}. "
        f"Evidence: {_bounded(weakness.evidence)}."
    )


def _recommendation_summary(
    recommendations: tuple[StudyRecommendation, ...],
) -> str:
    """Describe only the first planned activity and its allotted time."""

    if not recommendations:
        return "No recommended activity is available."
    recommendation = recommendations[0]
    minutes = (
        f"{recommendation.minutes} minutes"
        if recommendation.minutes is not None
        else "no configured duration"
    )
    return f"First recommended activity: {_bounded(recommendation.activity)} ({minutes})."


def _messages(
    analytics: AnalyticsResult,
    weaknesses: tuple[Weakness, ...],
    recommendations: tuple[StudyRecommendation, ...],
) -> list[dict[str, str]]:
    """Build the one bounded system/user prompt pair for local Mock guidance."""

    system = (
        "Provide a brief, factual learning explanation using only the supplied "
        "aggregate Reading and Writing evidence. Do not infer missing data, "
        "identify a learner, or claim an official IELTS assessment."
    )
    user = "\n".join(
        (
            _band_summary(analytics),
            _writing_summary(analytics),
            _reading_summary(analytics),
            _weakness_summary(weaknesses),
            _recommendation_summary(recommendations),
        )
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": _bounded(user, limit=_MAX_PROMPT_LENGTH)},
    ]


def _with_disclaimer(content: str) -> str:
    """Append the learning-only disclaimer when the provider did not include it."""

    clean_content = content.strip()
    if AI_ANALYSIS_DISCLAIMER in clean_content:
        return clean_content
    separator = "\n\n" if clean_content else ""
    return f"{clean_content}{separator}{AI_ANALYSIS_DISCLAIMER}"


def explain_analytics(
    analytics: AnalyticsResult,
    weaknesses: tuple[Weakness, ...],
    recommendations: tuple[StudyRecommendation, ...],
    *,
    provider: AIProvider | None = None,
) -> AIAnalysisExplanation:
    """Explain approved aggregate evidence through the local Mock provider only."""

    active_provider = provider if provider is not None else MockAIProvider()
    if active_provider.is_mock is False:
        raise AIAnalysisError("mock_provider_required")
    try:
        response = active_provider.generate(
            _messages(analytics, weaknesses, recommendations), json_mode=False
        )
    except AIProviderError as error:
        raise AIAnalysisError(error.code) from None
    return AIAnalysisExplanation(
        content=_with_disclaimer(response.content),
        provider=_bounded(active_provider.provider_name, limit=80).lower(),
        model_name=_bounded(active_provider.model_name, limit=120),
        is_mock=True,
    )
