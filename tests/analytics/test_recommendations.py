"""Behavior tests for pure deterministic seven-day recommendations."""

from __future__ import annotations

import pytest

from ielts_ai_coach.services.analytics import (
    AnalyticsResult,
    LearningBehavior,
    ReadingAnalytics,
    SkillScoreAnalytics,
    WritingAnalytics,
    WritingDimensionAnalytics,
)
from ielts_ai_coach.services.recommendations import (
    build_seven_day_recommendations,
)
from ielts_ai_coach.services.weakness_analyzer import Weakness


def _analytics(
    *,
    daily_study_minutes: int | None = 60,
    reading: ReadingAnalytics | None = None,
    writing_feedback_count: int = 1,
    skills: tuple[SkillScoreAnalytics, ...] = (),
) -> AnalyticsResult:
    """Build an immutable analytics snapshot without database access."""

    return AnalyticsResult(
        current_band=None,
        target_band=7.0,
        target_gap=None,
        overall_trend=(),
        skills=skills,
        reading=reading
        or ReadingAnalytics(
            attempt_count=1,
            correct=4,
            total=10,
            accuracy=0.4,
            error_counts=(("matching_heading", 3),),
            frequent_error_types=("matching_heading",),
            warnings=(),
        ),
        writing=WritingAnalytics(
            feedback_count=writing_feedback_count,
            dimensions=tuple(
                WritingDimensionAnalytics(name=name, latest_band=None, trend=())
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
            daily_study_minutes=daily_study_minutes,
        ),
    )


def _weaknesses() -> tuple[Weakness, ...]:
    """Build ordered analyzer-compatible Reading and Writing weaknesses."""

    return (
        Weakness(
            skill="reading",
            weakness="Reading Matching Heading accuracy needs improvement",
            severity="high",
            evidence="Submitted Reading: 4/10 correct (40%).",
            recommendation="Practise Matching Heading question types.",
        ),
        Weakness(
            skill="writing",
            weakness="Grammar improvement needed",
            severity="high",
            evidence="grammar band 5.5; target 7.0; gap 1.5.",
            recommendation="Prioritize targeted grammar practice.",
        ),
    )


def test_recommendations_cycle_ordered_weaknesses_for_seven_days() -> None:
    """Ordered weaknesses produce concrete repeated Reading and Writing actions."""

    analytics = _analytics(daily_study_minutes=60)
    items = build_seven_day_recommendations(analytics, _weaknesses())

    assert [item.day for item in items] == list(range(1, 8))
    assert len(items) == 7
    assert all(item.activity.strip() for item in items)
    assert all(
        item.minutes is None
        or item.minutes <= analytics.behavior.daily_study_minutes
        for item in items
    )
    assert "Matching Heading" in items[0].activity
    assert any(
        "Task 2" in item.activity and "grammar" in item.evidence.lower()
        for item in items
    )
    assert [item.skill for item in items] == [
        "reading",
        "writing",
        "reading",
        "writing",
        "reading",
        "writing",
        "reading",
    ]
    assert {item.minutes for item in items} == {36}


@pytest.mark.parametrize(
    ("daily_study_minutes", "expected_minutes"),
    [(15, 15), (20, 15), (60, 36), (None, None)],
)
def test_recommendation_minutes_follow_configured_daily_time(
    daily_study_minutes: int | None, expected_minutes: int | None
) -> None:
    """Recommendations preserve absent time and cap the calculated allocation."""

    analytics = _analytics(daily_study_minutes=daily_study_minutes)
    items = build_seven_day_recommendations(analytics, _weaknesses())

    assert {item.minutes for item in items} == {expected_minutes}
    assert all(
        item.minutes is None
        or item.minutes <= analytics.behavior.daily_study_minutes
        for item in items
    )


def test_reading_without_a_resolved_question_type_uses_general_activity() -> None:
    """Unrecognized Reading labels retain a concrete general Reading practice."""

    items = build_seven_day_recommendations(
        _analytics(),
        (
            Weakness(
                skill="reading",
                weakness="Reading accuracy needs improvement",
                severity="medium",
                evidence="Submitted Reading evidence is limited.",
                recommendation="Practise submitted Reading questions.",
            ),
        ),
    )

    assert items[0].activity == (
        "完成 1 篇原创 Academic Reading 限时练习并复盘全部错题"
    )


def test_no_weaknesses_rotate_concrete_baseline_actions() -> None:
    """No measured weakness still yields a seven-day maintenance schedule."""

    items = build_seven_day_recommendations(_analytics(), ())

    assert len(items) == 7
    assert [item.skill for item in items] == [
        "reading",
        "writing",
        "review",
        "progress",
        "reading",
        "writing",
        "review",
    ]
    assert "Academic Reading" in items[0].activity
    assert "Task 2" in items[1].activity
    assert "错题" in items[2].activity
    assert "进展" in items[3].activity
    assert all("weakness" not in item.evidence.lower() for item in items)


def test_missing_reading_and_writing_evidence_collects_baselines() -> None:
    """Missing evidence is stated as baseline collection rather than a weakness."""

    items = build_seven_day_recommendations(
        _analytics(
            reading=ReadingAnalytics(
                attempt_count=0,
                correct=0,
                total=0,
                accuracy=None,
                error_counts=(),
                frequent_error_types=(),
                warnings=(),
            ),
            writing_feedback_count=0,
        ),
        (),
    )

    assert "收集 Reading 基线数据" in items[0].activity
    assert "收集 Writing 基线数据" in items[1].activity
    assert "collect baseline data" in items[0].evidence.lower()
    assert "collect baseline data" in items[1].evidence.lower()


def test_recommendations_are_deterministic_and_ignore_low_unsupported_scores() -> None:
    """No unsupported Listening or Speaking score creates a targeted action."""

    analytics = _analytics(
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
        )
    )

    first = build_seven_day_recommendations(analytics, ())
    second = build_seven_day_recommendations(analytics, ())

    assert first == second
    assert all(item.skill not in {"listening", "speaking"} for item in first)
    assert all(
        "Listening" not in item.activity and "Speaking" not in item.activity
        for item in first
    )
