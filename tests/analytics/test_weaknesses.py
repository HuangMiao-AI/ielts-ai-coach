"""Behavior tests for deterministic, evidence-backed weakness analysis."""

from __future__ import annotations

from datetime import datetime

from ielts_ai_coach.services.analytics import (
    AnalyticsResult,
    LearningBehavior,
    ReadingAnalytics,
    ScorePoint,
    SkillScoreAnalytics,
    WritingAnalytics,
    WritingDimensionAnalytics,
)
from ielts_ai_coach.services.weakness_analyzer import analyze_weaknesses


def _analytics(
    *,
    reading: ReadingAnalytics | None = None,
    target_band: float | None = 7.0,
    dimensions: tuple[WritingDimensionAnalytics, ...] | None = None,
    skills: tuple[SkillScoreAnalytics, ...] = (),
) -> AnalyticsResult:
    """Build an AnalyticsResult using only Task 1 immutable DTOs."""

    return AnalyticsResult(
        current_band=None,
        target_band=target_band,
        target_gap=None,
        overall_trend=(),
        skills=skills,
        reading=reading
        or ReadingAnalytics(
            attempt_count=0,
            correct=0,
            total=0,
            accuracy=None,
            error_counts=(),
            frequent_error_types=(),
            warnings=(),
        ),
        writing=WritingAnalytics(
            feedback_count=1 if dimensions else 0,
            dimensions=dimensions
            or tuple(
                WritingDimensionAnalytics(
                    name=name, latest_band=None, trend=()
                )
                for name in (
                    "task_achievement",
                    "coherence",
                    "vocabulary",
                    "grammar",
                )
            ),
        ),
        behavior=LearningBehavior(
            streak_days=0,
            recent_minutes=0,
            daily_study_minutes=None,
        ),
    )


def _reading(correct: int, total: int) -> ReadingAnalytics:
    """Build submitted aggregate Reading evidence with no typed errors."""

    return ReadingAnalytics(
        attempt_count=1,
        correct=correct,
        total=total,
        accuracy=correct / total,
        error_counts=(),
        frequent_error_types=(),
        warnings=(),
    )


def test_reading_accuracy_thresholds_are_evidence_backed() -> None:
    """Reading severity changes only at the specified submitted-score bands."""

    reading_49 = analyze_weaknesses(_analytics(reading=_reading(49, 100)))[0]
    reading_50 = analyze_weaknesses(_analytics(reading=_reading(50, 100)))[0]
    reading_55 = analyze_weaknesses(_analytics(reading=_reading(55, 100)))[0]
    reading_60 = analyze_weaknesses(_analytics(reading=_reading(60, 100)))[0]
    reading_65 = analyze_weaknesses(_analytics(reading=_reading(65, 100)))[0]
    reading_70_weaknesses = analyze_weaknesses(
        _analytics(reading=_reading(70, 100))
    )

    assert reading_49.severity == "high"
    assert reading_50.severity == "medium"
    assert reading_55.severity == "medium"
    assert reading_60.severity == "low"
    assert reading_65.severity == "low"
    assert reading_49.weakness == "Reading accuracy needs improvement"
    assert "49/100" in reading_49.evidence
    assert "49%" in reading_49.evidence
    assert "errors: none" in reading_49.evidence
    assert not reading_70_weaknesses


def test_reading_frequent_error_types_are_named_without_answer_data() -> None:
    """Typed Reading evidence names tied error types without raw snapshots."""

    weaknesses = analyze_weaknesses(
        _analytics(
            reading=ReadingAnalytics(
                attempt_count=2,
                correct=4,
                total=10,
                accuracy=0.4,
                error_counts=(
                    ("matching_heading", 3),
                    ("multiple_choice", 3),
                ),
                frequent_error_types=("matching_heading", "multiple_choice"),
                warnings=(),
            )
        )
    )

    reading = weaknesses[0]
    for question_type in ("Matching Heading", "Multiple Choice"):
        assert question_type in reading.weakness
        assert question_type in reading.recommendation
    assert "4/10" in reading.evidence
    assert "40%" in reading.evidence
    assert "matching_heading=3" in reading.evidence
    assert "multiple_choice=3" in reading.evidence
    assert "user_answer" not in reading.evidence
    assert "correct_answer" not in reading.evidence


def test_writing_gaps_use_dimension_labels_and_sorted_severity() -> None:
    """Writing uses latest dimension gaps and deterministic result ordering."""

    weaknesses = analyze_weaknesses(
        _analytics(
            dimensions=(
                WritingDimensionAnalytics(
                    name="task_achievement", latest_band=6.0, trend=()
                ),
                WritingDimensionAnalytics(
                    name="coherence", latest_band=6.25, trend=()
                ),
                WritingDimensionAnalytics(
                    name="vocabulary", latest_band=6.5, trend=()
                ),
                WritingDimensionAnalytics(
                    name="grammar", latest_band=5.5, trend=()
                ),
            )
        )
    )

    grammar_gap = next(
        item for item in weaknesses if item.weakness == "Grammar improvement needed"
    )

    assert grammar_gap.weakness == "Grammar improvement needed"
    assert grammar_gap.severity == "high"
    assert "band 5.5" in grammar_gap.evidence
    assert "target 7.0" in grammar_gap.evidence
    assert "gap 1.5" in grammar_gap.evidence
    assert [(item.severity, item.skill, item.weakness) for item in weaknesses] == [
        ("high", "writing", "Grammar improvement needed"),
        ("medium", "writing", "Task Achievement improvement needed"),
        ("low", "writing", "Coherence improvement needed"),
        ("low", "writing", "Vocabulary improvement needed"),
    ]


def test_writing_gap_thresholds_exclude_met_targets() -> None:
    """Writing severity follows every positive target-gap boundary."""

    def writing_gap(band: float) -> tuple[str, str]:
        result = analyze_weaknesses(
            _analytics(
                dimensions=(
                    WritingDimensionAnalytics(
                        name="grammar", latest_band=band, trend=()
                    ),
                )
            )
        )
        return (
            result[0].severity if result else "none",
            result[0].weakness if result else "",
        )

    assert writing_gap(6.0) == ("medium", "Grammar improvement needed")
    assert writing_gap(5.51) == ("medium", "Grammar improvement needed")
    assert writing_gap(6.25) == ("low", "Grammar improvement needed")
    assert writing_gap(6.01) == ("low", "Grammar improvement needed")
    assert writing_gap(7.0) == ("none", "")


def test_writing_requires_target_even_with_dimension_evidence() -> None:
    """Writing evidence without a target cannot establish a target gap."""

    analytics = _analytics(
        target_band=None,
        dimensions=(
            WritingDimensionAnalytics(
                name="grammar", latest_band=5.5, trend=()
            ),
        ),
    )

    assert not analyze_weaknesses(analytics)


def test_writing_uses_latest_band_not_historical_trend() -> None:
    """Only the latest Writing band, rather than prior trend points, is analyzed."""

    analytics = _analytics(
        dimensions=(
            WritingDimensionAnalytics(
                name="grammar",
                latest_band=7.0,
                trend=(
                    ScorePoint(
                        recorded_at=datetime(2026, 1, 1, 9, 0),
                        band=4.0,
                    ),
                ),
            ),
        )
    )

    assert not analyze_weaknesses(analytics)


def test_equal_severity_results_use_reading_before_writing() -> None:
    """Equal severities are ordered by skill after severity ranking."""

    weaknesses = analyze_weaknesses(
        _analytics(
            reading=_reading(49, 100),
            dimensions=(
                WritingDimensionAnalytics(
                    name="grammar", latest_band=5.5, trend=()
                ),
            ),
        )
    )

    assert [(item.skill, item.severity) for item in weaknesses] == [
        ("reading", "high"),
        ("writing", "high"),
    ]


def test_absent_evidence_and_low_listening_speaking_scores_create_no_weaknesses() -> None:
    """Missing inputs and unsupported skills cannot produce inferred weaknesses."""

    analytics_with_low_section_scores = _analytics(
        reading=_reading(100, 100),
        skills=(
            SkillScoreAnalytics(
                skill="listening",
                latest_band=4.0,
                trend=(),
                detail_status="No detailed practice analytics available",
            ),
            SkillScoreAnalytics(
                skill="speaking",
                latest_band=4.0,
                trend=(),
                detail_status="No detailed practice analytics available",
            ),
        ),
    )

    assert not analyze_weaknesses(_analytics(target_band=None))
    assert not analyze_weaknesses(_analytics(reading=_reading(100, 100)))
    assert all(
        item.skill not in {"listening", "speaking"}
        for item in analyze_weaknesses(analytics_with_low_section_scores)
    )
