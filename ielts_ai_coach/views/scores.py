"""Simplified Chinese IELTS score entry and diagnosis page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import ScoreRecord, User
from ielts_ai_coach.services.learner_profiles import get_learner_profile
from ielts_ai_coach.services.scoring import (
    SUBJECT_LABELS,
    SUBJECTS,
    ScoreDiagnosis,
    ScoreValidationError,
    analyze_scores,
)
from ielts_ai_coach.services.scores import list_score_history, save_score_record


BAND_OPTIONS = [value / 2 for value in range(0, 19)]
EMPTY_BAND = "未填写"


def _record_scores(record: ScoreRecord) -> dict[str, float]:
    """Convert a score record into the standard subject dictionary."""

    return {
        "listening": record.listening,
        "reading": record.reading,
        "writing": record.writing,
        "speaking": record.speaking,
    }


def _profile_scores(profile) -> dict[str, float | None]:
    """Return independently optional baseline values from a learner profile."""

    return {
        "listening": profile.current_listening_band,
        "reading": profile.current_reading_band,
        "writing": profile.current_writing_band,
        "speaking": profile.current_speaking_band,
    }


def _render_diagnosis(diagnosis: ScoreDiagnosis) -> None:
    """Render a deterministic weakness diagnosis."""

    weak_labels = "、".join(
        SUBJECT_LABELS[subject] for subject in diagnosis.lowest_subjects
    )
    first, second, third = st.columns(3)
    first.metric("当前总分", f"{diagnosis.overall:.1f}")
    second.metric("当前弱项", weak_labels)
    third.metric("距离目标", f"{diagnosis.overall_gap:.1f} 分")

    st.subheader("规则化提升建议")
    for subject in diagnosis.lowest_subjects:
        with st.container(border=True):
            st.markdown(f"**{SUBJECT_LABELS[subject]} · {diagnosis.lowest_score:.1f}**")
            for recommendation in diagnosis.recommendations[subject]:
                st.write(f"- {recommendation}")


def _render_score_history(history: list[ScoreRecord]) -> None:
    """Render historical score records and a trend chart."""

    if not history:
        st.info("还没有成绩记录。录入最近一次模考成绩后即可查看趋势。")
        return

    st.subheader("成绩趋势")
    chart_rows = [
        {
            "日期": record.recorded_at.date().isoformat(),
            "总分": record.overall,
            "听力": record.listening,
            "阅读": record.reading,
            "写作": record.writing,
            "口语": record.speaking,
        }
        for record in reversed(history)
    ]
    st.vega_lite_chart(
        {
            "data": {"values": chart_rows},
            "transform": [
                {
                    "fold": ["总分", "听力", "阅读", "写作", "口语"],
                    "as": ["科目", "分数"],
                }
            ],
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {"field": "日期", "type": "temporal", "title": "记录日期"},
                "y": {
                    "field": "分数",
                    "type": "quantitative",
                    "scale": {"domain": [0, 9]},
                },
                "color": {"field": "科目", "type": "nominal"},
                "tooltip": [
                    {"field": "日期", "type": "temporal"},
                    {"field": "科目", "type": "nominal"},
                    {"field": "分数", "type": "quantitative"},
                ],
            },
        },
        use_container_width=True,
    )

    with st.expander("查看历史明细"):
        for row in reversed(chart_rows):
            st.write(
                f"{row['日期']} · 总分 {row['总分']:.1f} · "
                f"听力 {row['听力']:.1f} · 阅读 {row['阅读']:.1f} · "
                f"写作 {row['写作']:.1f} · 口语 {row['口语']:.1f}"
            )


def render_scores_page(user: User) -> None:
    """Render score input, latest diagnosis, and user-owned history."""

    profile = get_learner_profile(user.id)
    history = list_score_history(user.id)
    latest = history[0] if history else None

    st.title("成绩诊断")
    st.caption("总分和弱项由确定性规则计算，不使用AI。")
    if profile is None or not profile.onboarding_completed:
        st.warning("请先在“我的档案”中设置目标分和考试日期。")
        return

    defaults = _record_scores(latest) if latest else _profile_scores(profile)
    with st.form("score_record_form"):
        columns = st.columns(4)
        selected_scores: dict[str, str | float] = {}
        score_options: tuple[str | float, ...] = (
            EMPTY_BAND,
            *BAND_OPTIONS,
        )
        for column, subject in zip(columns, SUBJECTS):
            with column:
                default = defaults[subject]
                selected_scores[subject] = st.selectbox(
                    SUBJECT_LABELS[subject],
                    score_options,
                    index=(
                        score_options.index(float(default))
                        if default is not None
                        else 0
                    ),
                    key=f"score_{subject}",
                )
        note = st.text_input(
            "备注（可选）",
            max_chars=300,
            placeholder="例如：剑雅18 Test 2",
        )
        submitted = st.form_submit_button(
            "保存并诊断",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if any(
            value == EMPTY_BAND for value in selected_scores.values()
        ):
            st.error("请完整填写四科成绩；缺失项不会使用默认值补齐。")
            _render_score_history(history)
            return
        scores = {
            subject: float(selected_scores[subject])
            for subject in SUBJECTS
        }
        try:
            latest = save_score_record(
                user_id=user.id,
                scores=scores,
                note=note,
            )
        except (ScoreValidationError, ValueError):
            st.error("成绩格式无效，请使用0–9之间的0.5分档。")
        else:
            st.success("成绩已保存。")
            history = list_score_history(user.id)

    if latest is not None:
        diagnosis = analyze_scores(
            _record_scores(latest),
            target_overall=profile.target_overall_band,
        )
        _render_diagnosis(diagnosis)

    _render_score_history(history)
