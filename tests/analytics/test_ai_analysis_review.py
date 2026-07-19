"""Review regressions for the mock-only analytics explanation boundary."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ielts_ai_coach.services.recommendations import StudyRecommendation
from ielts_ai_coach.services.weakness_analyzer import Weakness, analyze_weaknesses
from tests.analytics.test_ai_analysis import (
    NonMockProvider,
    RecordingMockProvider,
    _analytics,
    _recommendations,
    _weaknesses,
)


class MalformedMockProvider(NonMockProvider):
    """Expose an invalid Mock flag and fail if generation is attempted."""

    @property
    def is_mock(self) -> bool:
        """Return an invalid provider flag to exercise fail-closed validation."""

        return None  # type: ignore[return-value]


def test_free_text_weakness_and_activity_values_fail_closed() -> None:
    """Unvalidated DTO text must never be forwarded to the local provider."""

    from ielts_ai_coach.services.ai_analysis import explain_analytics

    provider = RecordingMockProvider()
    private_weakness = Weakness(
        skill="reading",
        weakness="PRIVATE_WEAKNESS_TEXT",
        severity="high",
        evidence="PRIVATE_WEAKNESS_EVIDENCE",
        recommendation="PRIVATE_WEAKNESS_RECOMMENDATION",
    )
    private_recommendation = StudyRecommendation(
        day=1,
        skill="reading",
        activity="PRIVATE_RECOMMENDATION_ACTIVITY",
        minutes=36,
        evidence="PRIVATE_RECOMMENDATION_EVIDENCE",
    )

    explain_analytics(
        _analytics(),
        (private_weakness,),
        (private_recommendation,),
        provider=provider,
    )
    prompt = "\n".join(message["content"] for message in provider.messages)

    for private_value in (
        "PRIVATE_WEAKNESS_TEXT",
        "PRIVATE_WEAKNESS_EVIDENCE",
        "PRIVATE_WEAKNESS_RECOMMENDATION",
        "PRIVATE_RECOMMENDATION_ACTIVITY",
        "PRIVATE_RECOMMENDATION_EVIDENCE",
    ):
        assert private_value not in prompt
    assert "Reading Matching Heading accuracy needs improvement" in prompt
    assert "No validated recommended activity is available." in prompt


def test_validated_weakness_evidence_is_reconstructed_from_analytics() -> None:
    """A matching label uses analyzer evidence rather than supplied free text."""

    from ielts_ai_coach.services.ai_analysis import explain_analytics

    provider = RecordingMockProvider()
    supplied_weakness = replace(
        _weaknesses()[0], evidence="PRIVATE_SUPPLIED_WEAKNESS_EVIDENCE"
    )
    analytics = _analytics()

    explain_analytics(
        analytics,
        (supplied_weakness,),
        _recommendations(analytics, (supplied_weakness,)),
        provider=provider,
    )
    prompt = "\n".join(message["content"] for message in provider.messages)

    assert "PRIVATE_SUPPLIED_WEAKNESS_EVIDENCE" not in prompt
    assert "Submitted Reading: 12/20 correct (60%)" in prompt


def test_analyzer_reading_text_with_unknown_type_never_reaches_prompt() -> None:
    """Reading evidence must exclude unknown types from a real analyzer result."""

    from ielts_ai_coach.services.ai_analysis import explain_analytics

    analytics = replace(
        _analytics(),
        reading=replace(
            _analytics().reading,
            correct=4,
            total=10,
            accuracy=0.4,
            error_counts=(
                ("matching_heading", 4),
                ("PRIVATE_READING_ANSWER", 6),
            ),
            frequent_error_types=("matching_heading", "PRIVATE_READING_ANSWER"),
        ),
    )
    weaknesses = analyze_weaknesses(analytics)
    provider = RecordingMockProvider()

    explain_analytics(
        analytics,
        weaknesses,
        _recommendations(analytics, weaknesses),
        provider=provider,
    )

    assert weaknesses[0].skill == "reading"
    assert all(
        "PRIVATE_READING_ANSWER" not in message["content"]
        for message in provider.messages
    )
    assert "Matching Heading" in provider.messages[1]["content"]
    assert "Reading Matching Heading accuracy needs improvement" in provider.messages[1][
        "content"
    ]


def test_malformed_mock_flag_is_rejected_before_generate() -> None:
    """Any non-true Mock flag must be rejected without receiving prompt data."""

    from ielts_ai_coach.services.ai_analysis import AIAnalysisError, explain_analytics

    provider = MalformedMockProvider()

    with pytest.raises(AIAnalysisError, match="mock_provider_required"):
        explain_analytics(
            _analytics(), _weaknesses(), _recommendations(), provider=provider
        )

    assert provider.calls == 0


def test_duplicate_provider_disclaimers_are_normalized_to_one() -> None:
    """Provider output must contain the exact learning disclaimer once."""

    from ielts_ai_coach.services.ai_analysis import (
        AI_ANALYSIS_DISCLAIMER,
        explain_analytics,
    )

    provider = RecordingMockProvider(
        f"First note. {AI_ANALYSIS_DISCLAIMER}\nSecond note. "
        f"{AI_ANALYSIS_DISCLAIMER}"
    )

    result = explain_analytics(
        _analytics(), _weaknesses(), _recommendations(), provider=provider
    )

    assert result.content.count(AI_ANALYSIS_DISCLAIMER) == 1
