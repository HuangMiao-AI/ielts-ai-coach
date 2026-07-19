"""Behavior tests for the mock-only analytics explanation boundary."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from ielts_ai_coach.ai.base import AIProvider, AIProviderError, AIResponse
from ielts_ai_coach.services.analytics import (
    AnalyticsResult,
    LearningBehavior,
    ReadingAnalytics,
    WritingAnalytics,
    WritingDimensionAnalytics,
)
from ielts_ai_coach.services.recommendations import (
    StudyRecommendation,
    build_seven_day_recommendations,
)
from ielts_ai_coach.services.weakness_analyzer import Weakness


def _analytics(*, include_measurements: bool = True) -> AnalyticsResult:
    """Build an analytics snapshot without persistence or identity data."""

    return AnalyticsResult(
        current_band=6.0 if include_measurements else None,
        target_band=7.0 if include_measurements else None,
        target_gap=1.0 if include_measurements else None,
        overall_trend=(),
        skills=(),
        reading=ReadingAnalytics(
            attempt_count=2 if include_measurements else 0,
            correct=12 if include_measurements else 0,
            total=20 if include_measurements else 0,
            accuracy=0.6 if include_measurements else None,
            error_counts=(
                ("matching_heading", 4),
                ("multiple_choice", 2),
            )
            if include_measurements
            else (),
            frequent_error_types=("matching_heading",) if include_measurements else (),
            warnings=(),
        ),
        writing=WritingAnalytics(
            feedback_count=1 if include_measurements else 0,
            dimensions=tuple(
                WritingDimensionAnalytics(
                    name=name,
                    latest_band=band if include_measurements else None,
                    trend=(),
                )
                for name, band in (
                    ("task_achievement", 5.5),
                    ("coherence", 6.0),
                    ("vocabulary", 6.0),
                    ("grammar", 5.5),
                )
            ),
        ),
        behavior=LearningBehavior(
            streak_days=0,
            recent_minutes=0,
            daily_study_minutes=60 if include_measurements else None,
        ),
    )


def _weaknesses() -> tuple[Weakness, ...]:
    """Return an ordered safe weakness fixture."""

    return (
        Weakness(
            skill="reading",
            weakness="Reading Matching Heading accuracy needs improvement",
            severity="high",
            evidence="Submitted Reading: 12/20 correct (60%); errors: matching_heading=4.",
            recommendation="Practise Matching Heading question types.",
        ),
    )


def _recommendations(
    analytics: AnalyticsResult | None = None,
    weaknesses: tuple[Weakness, ...] | None = None,
) -> tuple[StudyRecommendation, ...]:
    """Return one display-only safe action fixture."""

    return build_seven_day_recommendations(
        analytics or _analytics(), weaknesses or _weaknesses()
    )


class RecordingMockProvider(AIProvider):
    """Capture one local call and return configurable response metadata."""

    def __init__(self, content: str = "Focus on the first action today.") -> None:
        self.content = content
        self.calls = 0
        self.messages: list[dict[str, str]] = []
        self.json_mode: bool | None = None

    @property
    def provider_name(self) -> str:
        return "recording-mock"

    @property
    def model_name(self) -> str:
        return "recording-mock-v1"

    @property
    def is_mock(self) -> bool:
        return True

    def generate(
        self, messages: list[dict[str, str]], *, json_mode: bool = False
    ) -> AIResponse:
        self.calls += 1
        self.messages = messages
        self.json_mode = json_mode
        return AIResponse(self.content, "untrusted-response", "untrusted-model")


class NonMockProvider(RecordingMockProvider):
    """Fail if a non-local provider is ever invoked."""

    @property
    def is_mock(self) -> bool:
        return False

    def generate(
        self, messages: list[dict[str, str]], *, json_mode: bool = False
    ) -> AIResponse:
        self.calls += 1
        raise AssertionError("A non-Mock provider must not be called.")


class FailingMockProvider(RecordingMockProvider):
    """Raise a safe provider error after prompt construction."""

    def generate(
        self, messages: list[dict[str, str]], *, json_mode: bool = False
    ) -> AIResponse:
        self.calls += 1
        raise AIProviderError("network_unavailable")


def test_default_explanation_uses_the_local_mock_and_disclaimer() -> None:
    """The default path must stay local and provide an educational disclaimer."""

    from ielts_ai_coach.services.ai_analysis import (
        AI_ANALYSIS_DISCLAIMER,
        explain_analytics,
    )

    result = explain_analytics(_analytics(), _weaknesses(), _recommendations())

    assert result.provider == "mock"
    assert result.is_mock is True
    assert "Writing" in result.content or "写作" in result.content
    assert AI_ANALYSIS_DISCLAIMER in result.content


def test_non_mock_provider_is_rejected_before_generate() -> None:
    """Configured or injected remote providers must receive no prompt data."""

    from ielts_ai_coach.services.ai_analysis import AIAnalysisError, explain_analytics

    non_mock_provider = NonMockProvider()

    with pytest.raises(AIAnalysisError, match="mock_provider_required"):
        explain_analytics(
            _analytics(),
            _weaknesses(),
            _recommendations(),
            provider=non_mock_provider,
        )

    assert non_mock_provider.calls == 0


def test_recording_mock_receives_only_bounded_aggregate_evidence() -> None:
    """The one prompt allows aggregate evidence and excludes private sentinels."""

    from ielts_ai_coach.services.ai_analysis import (
        AI_ANALYSIS_DISCLAIMER,
        explain_analytics,
    )

    provider = RecordingMockProvider()
    analytics = _analytics()
    analytics = replace(
        analytics,
        reading=replace(
            analytics.reading,
            frequent_error_types=("matching_heading", "PRIVATE_READING_ANSWER"),
        ),
        writing=replace(
            analytics.writing,
            dimensions=analytics.writing.dimensions
            + (
                WritingDimensionAnalytics(
                    name="PRIVATE_ESSAY_CONTENT", latest_band=9.0, trend=()
                ),
            ),
        ),
    )
    object.__setattr__(analytics, "username", "PRIVATE_USERNAME")
    object.__setattr__(analytics, "recording", "PRIVATE_RECORDING")
    result = explain_analytics(
        analytics, _weaknesses(), _recommendations(), provider=provider
    )
    prompt = "\n".join(message["content"] for message in provider.messages)

    assert provider.calls == 1
    assert provider.json_mode is False
    assert "12/20" in prompt
    assert "Matching Heading" in prompt
    assert _recommendations()[0].activity in prompt
    assert "36 minutes" in prompt
    for private_value in (
        "PRIVATE_ESSAY_CONTENT",
        "PRIVATE_READING_ANSWER",
        "PRIVATE_USERNAME",
        "PRIVATE_RECORDING",
    ):
        assert private_value not in prompt
    assert result.provider == "untrusted-response"
    assert result.model_name == "untrusted-model"
    assert result.content.count(AI_ANALYSIS_DISCLAIMER) == 1


def test_provider_error_exposes_only_its_safe_code() -> None:
    """Raw provider failures must not escape the local explanation boundary."""

    from ielts_ai_coach.services.ai_analysis import AIAnalysisError, explain_analytics

    with pytest.raises(AIAnalysisError, match="network_unavailable"):
        explain_analytics(
            _analytics(),
            _weaknesses(),
            _recommendations(),
            provider=FailingMockProvider(),
        )


def test_empty_data_prompt_states_missing_measurements_without_inference() -> None:
    """Absent evidence must be factual rather than invented for the provider."""

    from ielts_ai_coach.services.ai_analysis import explain_analytics

    provider = RecordingMockProvider()
    explain_analytics(_analytics(include_measurements=False), (), (), provider=provider)
    prompt = "\n".join(message["content"] for message in provider.messages)

    assert "No current or target band measurement is available." in prompt
    assert "No submitted Reading aggregate is available." in prompt
    assert "No latest Writing dimension bands are available." in prompt
    assert "No measured weakness is available." in prompt
    assert "No recommended activity is available." in prompt
    assert "12/20" not in prompt


def test_service_imports_do_not_cross_the_mock_only_boundary() -> None:
    """The service must not select configured providers or use HTTP dependencies."""

    source_path = (
        Path(__file__).resolve().parents[2]
        / "ielts_ai_coach"
        / "services"
        / "ai_analysis.py"
    )
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source_path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert "get_ai_provider" not in imports
    assert "qwen" not in imports
    assert "requests" not in imports
    assert "config" not in imports
