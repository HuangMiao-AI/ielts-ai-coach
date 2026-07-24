"""Pure display formatting for the Home growth dashboard."""

from __future__ import annotations

from html import escape

from ielts_ai_coach.services.analytics import AnalyticsResult, ScorePoint
from ielts_ai_coach.services.recommendations import StudyRecommendation
from ielts_ai_coach.services.weakness_analyzer import Weakness


SCORE_SKILL_LABELS = {
    "listening": "听力",
    "reading": "阅读",
    "writing": "写作",
    "speaking": "口语",
}
READING_TYPE_LABELS = {
    "matching_heading": "Matching Heading",
    "multiple_choice": "Multiple Choice",
    "true_false_not_given": "True/False/Not Given",
}
WRITING_DIMENSION_LABELS = {
    "task_achievement": "Task Achievement",
    "coherence": "Coherence",
    "vocabulary": "Vocabulary",
    "grammar": "Grammar",
}
_SEVERITY_LABELS = {"low": "低", "medium": "中", "high": "高"}
_SKILL_LABELS = {"reading": "阅读", "writing": "写作"}
_WRITING_WEAKNESS_LABELS = {
    "Task Achievement improvement needed": "Task Achievement 需要提高",
    "Coherence improvement needed": "Coherence 需要提高",
    "Vocabulary improvement needed": "Vocabulary 需要提高",
    "Grammar improvement needed": "Grammar 需要提高",
}


def format_band(value: float | None) -> str:
    """Format a measured band or an honest unavailable value."""

    return f"{value:.1f}" if value is not None else "暂无"


def format_gap(analytics: AnalyticsResult) -> str:
    """Format the measured target gap without implying missing performance."""

    gap = analytics.target_gap
    if gap is None:
        return "暂无"
    if gap > 0:
        return f"{gap:.1f} 分"
    if gap < 0:
        return f"已超出 {abs(gap):.1f} 分"
    return "已达目标"


def format_trend(points: tuple[ScorePoint, ...]) -> str:
    """Format at most three chronological score points for compact display."""

    bands = [f"{point.band:.1f}" for point in points[-3:]]
    return " → ".join(bands) if bands else "暂无"


def _localized_weakness(weakness: Weakness) -> tuple[str, str, str]:
    """Translate deterministic weakness fields for the Chinese student UI."""

    if weakness.skill == "reading":
        question_type = (
            weakness.weakness.removeprefix("Reading ")
            .removesuffix(" accuracy needs improvement")
        )
        weakness_text = (
            f"阅读 {question_type} 正确率需要提高"
            if question_type
            else "阅读正确率需要提高"
        )
        evidence = (
            weakness.evidence.replace("Submitted Reading: ", "已提交 Reading：")
            .replace(" correct (", " 正确（")
            .replace("); errors: ", "）；错误：")
            .removesuffix(".")
            + "。"
        )
        recommendation = (
            f"练习 {question_type} 题型并复盘错误模式。"
            if question_type
            else "练习已提交的 Reading 题目并复盘错误模式。"
        )
        return weakness_text, evidence, recommendation

    weakness_text = _WRITING_WEAKNESS_LABELS.get(
        weakness.weakness, weakness.weakness
    )
    dimension = weakness.weakness.removesuffix(" improvement needed")
    evidence = (
        weakness.evidence.replace(f"{dimension.lower()} band ", f"{dimension}：")
        .replace("; target ", "；目标：")
        .replace("; gap ", "；差距：")
        .removesuffix(".")
        + "。"
    )
    recommendation = (
        f"优先进行 {dimension} 针对性练习，再提交下一次 Writing 反馈。"
    )
    return weakness_text, evidence, recommendation


def weakness_card_html(weakness: Weakness) -> str:
    """Return escaped display HTML for one evidence-backed weakness."""

    severity = weakness.severity
    skill = _SKILL_LABELS.get(weakness.skill, weakness.skill)
    weakness_text, evidence, recommendation = _localized_weakness(weakness)
    return (
        '<article class="glass-card growth-weakness-card '
        f'severity-{severity}" data-severity="{severity}">'
        f"<p>科目：{escape(skill)}</p>"
        f"<p>弱项：{escape(weakness_text)}</p>"
        f"<p>严重程度：{_SEVERITY_LABELS[severity]}</p>"
        f"<p>证据：{escape(evidence)}</p>"
        f"<p>建议：{escape(recommendation)}</p>"
        "</article>"
    )


def recommendation_card_html(item: StudyRecommendation) -> str:
    """Return escaped display HTML for one concrete next action."""

    minutes = (
        f"<p>时长：{item.minutes} 分钟</p>"
        if item.minutes is not None
        else ""
    )
    return (
        '<article class="glass-card growth-recommendation-card">'
        f"<p>第 {item.day} 天</p>"
        f"<p>活动：{escape(item.activity)}</p>"
        f"{minutes}</article>"
    )
