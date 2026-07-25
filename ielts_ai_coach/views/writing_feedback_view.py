"""Read-only rendering for stored Writing feedback."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.ai.writing_evaluator import WRITING_DISCLAIMER
from ielts_ai_coach.database.models import WritingFeedback


def render_feedback(feedback: WritingFeedback) -> None:
    """Render one validated structured writing report."""

    if feedback.provider.casefold() == "mock":
        st.warning("Demo feedback · 固定示例，不代表真实AI评分或官方成绩。")
    st.error(WRITING_DISCLAIMER)
    columns = st.columns(5)
    labels = (
        ("任务回应", feedback.task_response_or_achievement),
        ("连贯衔接", feedback.coherence_and_cohesion),
        ("词汇资源", feedback.lexical_resource),
        ("语法准确", feedback.grammatical_range_and_accuracy),
        ("预估总分", feedback.estimated_overall),
    )
    for column, (label, score) in zip(columns, labels):
        column.metric(label, f"{score:.1f}")
    first, second = st.columns(2)
    with first:
        st.subheader("做得好的地方")
        for item in feedback.strengths:
            st.write(f"- {item}")
    with second:
        st.subheader("主要问题")
        for item in feedback.main_issues:
            st.write(f"- {item}")
    st.subheader("具体修改建议")
    for item in feedback.actionable_suggestions:
        st.write(f"- {item}")
    st.subheader("单段改写示例")
    st.info(feedback.rewrite_example)
