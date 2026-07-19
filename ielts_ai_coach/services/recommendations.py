"""Pure deterministic seven-day study recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from ielts_ai_coach.services.analytics import AnalyticsResult
from ielts_ai_coach.services.weakness_analyzer import Weakness


READING_ACTIVITIES = {
    "matching_heading": "完成 1 组原创 Reading Matching Heading，并逐题记录段落主旨与干扰项原因",
    "multiple_choice": "完成 1 组原创 Reading Multiple Choice，并标出定位词和同义替换",
    "true_false_not_given": "完成 1 组原创 Reading TFNG，并分别记录 False 与 Not Given 的证据边界",
    "general": "完成 1 篇原创 Academic Reading 限时练习并复盘全部错题",
}
WRITING_ACTIVITIES = {
    "task_achievement": "完成 1 份 Writing Task 2 提纲，检查立场、论点和例证是否完整回应题目",
    "coherence": "重写 1 个 Writing Task 2 主体段，明确主题句、论证顺序和衔接",
    "vocabulary": "整理 10 个 Writing Task 2 主题词组，并各写 1 个准确例句",
    "grammar": "复查 1 个 Writing Task 2 主体段的主谓一致、冠词、从句和标点",
}

_READING_LABELS = {
    "matching_heading": "Matching Heading",
    "multiple_choice": "Multiple Choice",
    "true_false_not_given": "True/False/Not Given",
}
_WRITING_WEAKNESS_LABELS = {
    "task_achievement": "Task Achievement improvement needed",
    "coherence": "Coherence improvement needed",
    "vocabulary": "Vocabulary improvement needed",
    "grammar": "Grammar improvement needed",
}


@dataclass(frozen=True)
class StudyRecommendation:
    """One display-only activity for a day of the recommendation cycle."""

    day: int
    skill: str
    activity: str
    minutes: int | None
    evidence: str


def _recommendation_minutes(analytics: AnalyticsResult) -> int | None:
    """Allocate the approved portion of a valid configured daily study time."""

    daily_minutes = analytics.behavior.daily_study_minutes
    if daily_minutes is None:
        return None
    return max(15, min(daily_minutes, round(daily_minutes * 0.6)))


def _reading_activity(weakness: Weakness) -> str:
    """Select the named Reading question-type activity, or general practice."""

    matches = (
        (weakness.weakness.find(label), question_type)
        for question_type, label in _READING_LABELS.items()
        if weakness.weakness.find(label) >= 0
    )
    _, question_type = min(matches, default=(0, "general"))
    return READING_ACTIVITIES[question_type]


def _writing_activity(weakness: Weakness) -> str:
    """Select the exact Writing dimension activity from its weakness label."""

    for dimension, label in _WRITING_WEAKNESS_LABELS.items():
        if weakness.weakness == label:
            return WRITING_ACTIVITIES[dimension]
    return "完成 1 个 Writing Task 2 基线段落检查，复核立场、论证和语言准确性"


def _weakness_recommendation(
    day: int, weakness: Weakness, minutes: int | None
) -> StudyRecommendation:
    """Translate one approved Reading or Writing weakness into one action."""

    if weakness.skill == "reading":
        activity = _reading_activity(weakness)
    else:
        activity = _writing_activity(weakness)
    return StudyRecommendation(
        day=day,
        skill=weakness.skill,
        activity=activity,
        minutes=minutes,
        evidence=weakness.evidence,
    )


def _baseline_actions(analytics: AnalyticsResult) -> tuple[tuple[str, str, str], ...]:
    """Return maintenance actions without claiming an unmeasured weakness."""

    reading_missing = analytics.reading.attempt_count == 0
    writing_missing = analytics.writing.feedback_count == 0
    reading_activity = (
        "完成 1 篇原创 Academic Reading 基线限时练习，收集 Reading 基线数据并复盘全部错题"
        if reading_missing
        else READING_ACTIVITIES["general"]
    )
    reading_evidence = (
        "Reading evidence is missing; collect baseline data before making a targeted recommendation."
        if reading_missing
        else "Use submitted Reading evidence to maintain current practice quality."
    )
    writing_activity = (
        "完成 1 个 Writing Task 2 基线段落检查，收集 Writing 基线数据"
        if writing_missing
        else "完成 1 个 Writing Task 2 基线段落检查，复核立场、论证和语言准确性"
    )
    writing_evidence = (
        "Writing evidence is missing; collect baseline data before making a targeted recommendation."
        if writing_missing
        else "Use submitted Writing feedback to maintain current practice quality."
    )
    return (
        ("reading", reading_activity, reading_evidence),
        ("writing", writing_activity, writing_evidence),
        ("review", "复盘已保存的错题或反馈，记录 3 个可执行改进点", "Review saved errors or feedback without inferring a new issue."),
        ("progress", "回顾本周学习进展，记录下一周的 1 个可执行目标", "Review recorded progress without inferring a new issue."),
    )


def _baseline_recommendations(
    analytics: AnalyticsResult, minutes: int | None
) -> tuple[StudyRecommendation, ...]:
    """Cycle baseline and maintenance actions to fill the seven-day display."""

    actions = _baseline_actions(analytics)
    return tuple(
        StudyRecommendation(
            day=day,
            skill=skill,
            activity=activity,
            minutes=minutes,
            evidence=evidence,
        )
        for day, (skill, activity, evidence) in enumerate(
            (actions[index % len(actions)] for index in range(7)), start=1
        )
    )


def build_seven_day_recommendations(
    analytics: AnalyticsResult,
    weaknesses: tuple[Weakness, ...],
) -> tuple[StudyRecommendation, ...]:
    """Build seven display recommendations from supplied Reading/Writing evidence."""

    minutes = _recommendation_minutes(analytics)
    actionable_weaknesses = tuple(
        weakness for weakness in weaknesses if weakness.skill in {"reading", "writing"}
    )
    if not actionable_weaknesses:
        return _baseline_recommendations(analytics, minutes)
    return tuple(
        _weakness_recommendation(
            day,
            actionable_weaknesses[(day - 1) % len(actionable_weaknesses)],
            minutes,
        )
        for day in range(1, 8)
    )
