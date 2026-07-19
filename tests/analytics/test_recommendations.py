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


@pytest.mark.parametrize(
    ("weakness", "expected_activity"),
    [
        pytest.param(Weakness("reading", "Reading Matching Heading accuracy needs improvement", "high", "matching evidence", "Practice matching."), "完成 1 组原创 Reading Matching Heading，并逐题记录段落主旨与干扰项原因", id="matching-heading"),
        pytest.param(Weakness("reading", "Reading Multiple Choice accuracy needs improvement", "high", "multiple-choice evidence", "Practice multiple choice."), "完成 1 组原创 Reading Multiple Choice，并标出定位词和同义替换", id="multiple-choice"),
        pytest.param(Weakness("reading", "Reading True/False/Not Given accuracy needs improvement", "high", "tfng evidence", "Practice TFNG."), "完成 1 组原创 Reading TFNG，并分别记录 False 与 Not Given 的证据边界", id="tfng"),
        pytest.param(Weakness("writing", "Task Achievement improvement needed", "high", "task-achievement evidence", "Practice task achievement."), "完成 1 份 Writing Task 2 提纲，检查立场、论点和例证是否完整回应题目", id="task-achievement"),
        pytest.param(Weakness("writing", "Coherence improvement needed", "medium", "coherence evidence", "Practice coherence."), "重写 1 个 Writing Task 2 主体段，明确主题句、论证顺序和衔接", id="coherence"),
        pytest.param(Weakness("writing", "Vocabulary improvement needed", "low", "vocabulary evidence", "Practice vocabulary."), "整理 10 个 Writing Task 2 主题词组，并各写 1 个准确例句", id="vocabulary"),
        pytest.param(Weakness("writing", "Grammar improvement needed", "high", "grammar evidence", "Practice grammar."), "复查 1 个 Writing Task 2 主体段的主谓一致、冠词、从句和标点", id="grammar"),
    ],
)
def test_weakness_labels_use_exact_mapped_activities(
    weakness: Weakness, expected_activity: str
) -> None:
    """Every supported analyzer label selects its exact concrete activity."""

    items = build_seven_day_recommendations(_analytics(), (weakness,))

    assert items[0].activity == expected_activity


def test_recommendations_preserve_injected_non_natural_weakness_order() -> None:
    """Fault-injected, non-analyzer ordering is repeated without internal sorting."""

    injected_weaknesses = (
        Weakness("writing", "Vocabulary improvement needed", "low", "injected vocabulary evidence", "Practice vocabulary."),
        Weakness("reading", "Reading True/False/Not Given accuracy needs improvement", "high", "injected tfng evidence", "Practice TFNG."),
        Weakness("writing", "Grammar improvement needed", "high", "injected grammar evidence", "Practice grammar."),
    )

    items = build_seven_day_recommendations(_analytics(), injected_weaknesses)

    assert [(item.activity, item.evidence) for item in items] == [
        ("整理 10 个 Writing Task 2 主题词组，并各写 1 个准确例句", "injected vocabulary evidence"),
        ("完成 1 组原创 Reading TFNG，并分别记录 False 与 Not Given 的证据边界", "injected tfng evidence"),
        ("复查 1 个 Writing Task 2 主体段的主谓一致、冠词、从句和标点", "injected grammar evidence"),
        ("整理 10 个 Writing Task 2 主题词组，并各写 1 个准确例句", "injected vocabulary evidence"),
        ("完成 1 组原创 Reading TFNG，并分别记录 False 与 Not Given 的证据边界", "injected tfng evidence"),
        ("复查 1 个 Writing Task 2 主体段的主谓一致、冠词、从句和标点", "injected grammar evidence"),
        ("整理 10 个 Writing Task 2 主题词组，并各写 1 个准确例句", "injected vocabulary evidence"),
    ]


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


@pytest.mark.parametrize(
    ("analytics", "missing_index", "present_index", "missing_skill"),
    [
        pytest.param(
            _analytics(
                reading=ReadingAnalytics(0, 0, 0, None, (), (), ()),
                writing_feedback_count=1,
            ),
            0,
            1,
            "Reading",
            id="reading-only-missing",
        ),
        pytest.param(
            _analytics(writing_feedback_count=0),
            1,
            0,
            "Writing",
            id="writing-only-missing",
        ),
    ],
)
def test_only_missing_skill_collects_baseline_data(
    analytics: AnalyticsResult,
    missing_index: int,
    present_index: int,
    missing_skill: str,
) -> None:
    """Independent missing evidence cases affect only the absent skill action."""

    items = build_seven_day_recommendations(analytics, ())

    assert f"收集 {missing_skill} 基线数据" in items[missing_index].activity
    assert "collect baseline data" in items[missing_index].evidence.lower()
    assert "基线数据" not in items[present_index].activity
    assert "collect baseline data" not in items[present_index].evidence.lower()


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
