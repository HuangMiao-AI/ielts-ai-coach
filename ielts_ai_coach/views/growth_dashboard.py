"""Read-only IELTS growth analytics for the authenticated Home page."""

from __future__ import annotations

from datetime import date
from html import escape

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.services.ai_analysis import explain_analytics
from ielts_ai_coach.services.analytics import (
    AnalyticsResult,
    build_analytics_result,
)
from ielts_ai_coach.services.recommendations import (
    StudyRecommendation,
    build_seven_day_recommendations,
)
from ielts_ai_coach.services.weakness_analyzer import Weakness, analyze_weaknesses
from ielts_ai_coach.views.growth_dashboard_content import (
    READING_TYPE_LABELS,
    SCORE_SKILL_LABELS,
    WRITING_DIMENSION_LABELS,
    format_band,
    format_gap,
    format_trend,
    recommendation_card_html,
    weakness_card_html,
)


def _section(title: str) -> None:
    """Render one shared-style growth dashboard heading."""

    st.markdown(
        f'<div class="section-heading">{escape(title)}</div>',
        unsafe_allow_html=True,
    )


def _format_progress(analytics: AnalyticsResult) -> str:
    """Format bounded progress only when current and target bands exist."""

    current = analytics.current_band
    target = analytics.target_band
    if current is None or target is None or target <= 0:
        return "暂无"
    return f"{min(100.0, current / target * 100):.0f}%"


def _render_metrics(analytics: AnalyticsResult) -> None:
    """Render the approved growth summary metrics and factual target gap."""

    with st.container(key="growth-dashboard-grid"):
        columns = st.columns(5)
        values = (
            ("Current Band", format_band(analytics.current_band)),
            ("Target Band", format_band(analytics.target_band)),
            ("当前差距", format_gap(analytics)),
            ("Progress", _format_progress(analytics)),
            ("Learning Streak", f"{analytics.behavior.streak_days} 天"),
        )
        for column, (label, value) in zip(columns, values):
            column.metric(label, value)


def _render_score_trends(analytics: AnalyticsResult) -> None:
    """Render latest section scores and measured chronological trends."""

    _section("四科最新成绩与趋势")
    cards = []
    for skill in analytics.skills:
        label = SCORE_SKILL_LABELS[skill.skill]
        latest = format_band(skill.latest_band)
        status = (
            f"<p>{escape(skill.detail_status)}</p>"
            if skill.detail_status
            else ""
        )
        cards.append(
            '<article class="glass-card growth-score-card">'
            f"<p>{label}：{latest}</p>"
            f"<p>趋势：{format_trend(skill.trend)}</p>"
            f"{status}</article>"
        )
    st.markdown(
        f'<div class="growth-dashboard-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _render_reading_details(analytics: AnalyticsResult) -> None:
    """Render aggregate Reading evidence without exposing answer content."""

    _section("Reading 细粒度表现")
    reading = analytics.reading
    if reading.attempt_count == 0 or reading.accuracy is None:
        st.caption("暂无已提交的 Reading 练习数据。")
        return
    frequent = "、".join(
        READING_TYPE_LABELS.get(item, item)
        for item in reading.frequent_error_types
    ) or "暂无高频错误类型"
    errors = "；".join(
        f"{READING_TYPE_LABELS.get(item, item)} {count}"
        for item, count in reading.error_counts
    ) or "无"
    st.markdown(
        '<article class="glass-card growth-reading-card">'
        f"<p>已提交练习：{reading.attempt_count} 次</p>"
        f"<p>正确题数：{reading.correct}/{reading.total}</p>"
        f"<p>正确率：{reading.accuracy * 100:.0f}%</p>"
        f"<p>高频错误：{escape(frequent)}</p>"
        f"<p>错误类型：{escape(errors)}</p>"
        "</article>",
        unsafe_allow_html=True,
    )


def _render_writing_details(analytics: AnalyticsResult) -> None:
    """Render the latest four Writing dimensions and measured trends."""

    _section("Writing 四项分析")
    if analytics.writing.feedback_count == 0:
        st.caption("暂无已完成的 Writing 反馈数据。")
        return
    cards = [
        '<article class="glass-card growth-writing-card">'
        f"<p>{WRITING_DIMENSION_LABELS[dimension.name]}："
        f"{format_band(dimension.latest_band)}</p>"
        f"<p>趋势：{format_trend(dimension.trend)}</p>"
        "</article>"
        for dimension in analytics.writing.dimensions
    ]
    st.markdown(
        f'<div class="growth-dashboard-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _render_weaknesses(weaknesses: tuple[Weakness, ...]) -> None:
    """Render weakness cards or a factual no-measured-weakness state."""

    _section("Weakness Cards")
    if not weaknesses:
        st.caption("暂无基于已提交阅读或写作数据识别的弱项。")
        return
    st.markdown(
        '<div class="growth-dashboard-grid">'
        + "".join(weakness_card_html(weakness) for weakness in weaknesses)
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_recommendations(
    recommendations: tuple[StudyRecommendation, ...],
) -> None:
    """Render only the first three deterministic next actions."""

    _section("Recommended Next Actions")
    st.markdown(
        '<div class="growth-dashboard-grid">'
        + "".join(
            recommendation_card_html(item) for item in recommendations[:3]
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_seven_day_summary(
    recommendations: tuple[StudyRecommendation, ...],
) -> None:
    """Render the complete deterministic seven-day display plan."""

    _section("未来 7 天建议摘要")
    st.markdown(
        '<div class="growth-dashboard-grid">'
        + "".join(recommendation_card_html(item) for item in recommendations)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_growth_dashboard(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
    today: date | None = None,
) -> None:
    """Render the user-scoped, read-only IELTS Growth Dashboard."""

    analytics = build_analytics_result(
        user_id,
        session_factory=session_factory,
        today=today,
    )
    weaknesses = analyze_weaknesses(analytics)
    recommendations = build_seven_day_recommendations(analytics, weaknesses)
    explanation = explain_analytics(analytics, weaknesses, recommendations)

    _section("IELTS Growth Dashboard")
    _render_metrics(analytics)
    _render_score_trends(analytics)
    _render_reading_details(analytics)
    _render_writing_details(analytics)
    _render_weaknesses(weaknesses)
    _render_recommendations(recommendations)
    _render_seven_day_summary(recommendations)
    _section("Mock AI Explanation")
    st.info(explanation.content)
