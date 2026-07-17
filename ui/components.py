"""Small rendering components shared by the Streamlit page."""

from html import escape
from typing import Any

import streamlit as st

from config import SUBJECT_LABELS
from models import AnalysisResult, StudyRecord


def render_hero() -> None:
    st.markdown(
        """
        <div class="coach-hero">
            <div class="coach-kicker">IELTS PERSONAL COACH</div>
            <h1>让每一分钟，都学在关键处。</h1>
            <p>输入四科成绩，马上获得弱项分析、学习建议和一周计划。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary(
    student_name: str, analysis: AnalysisResult, daily_minutes: int
) -> None:
    lowest_labels = "、".join(
        SUBJECT_LABELS[subject] for subject in analysis.lowest_subjects
    )
    st.markdown(
        f'<div class="section-title">{escape(student_name)}，这是你的学习诊断</div>',
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("预估总分", f"{analysis.overall_band:.1f}")
    col2.metric("当前弱项", lowest_labels)
    col3.metric("每日投入", f"{daily_minutes} 分钟")


def render_recommendations(analysis: AnalysisResult) -> None:
    st.markdown('<div class="section-title">优先提升建议</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-subtitle">先集中解决最低分科目，再逐步拉高总分。</p>',
        unsafe_allow_html=True,
    )
    for subject in analysis.lowest_subjects:
        items = "".join(
            f"<li>{escape(item)}</li>" for item in analysis.recommendations[subject]
        )
        st.markdown(
            f"""
            <div class="advice-card">
                <h4>{SUBJECT_LABELS[subject]} · {analysis.lowest_score:.1f} 分</h4>
                <ul>{items}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

def render_plan(plan: dict[str, Any]) -> None:
    st.markdown('<div class="section-title">你的每日学习节奏</div>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-subtitle">时间已经按弱项优先原则分配，四个环节加起来就是你设定的每日时长。</p>',
        unsafe_allow_html=True,
    )
    for block in plan["daily_blocks"]:
        st.markdown(
            f"""
            <div class="plan-card">
                <h4><span class="plan-time">{block['minutes']} 分钟</span>{escape(block['title'])}</h4>
                <div>{escape(block['detail'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">7 天执行计划</div>', unsafe_allow_html=True)
    for item in plan["weekly_plan"]:
        with st.expander(f"{item['day']} · {item['focus']}"):
            st.write(item["goal"])
            st.caption(f"建议学习 {item['minutes']} 分钟")


def render_history(records: list[StudyRecord]) -> None:
    st.markdown('<div class="section-title">最近学习记录</div>', unsafe_allow_html=True)
    if not records:
        st.info("还没有保存记录。生成方案后点击保存，就能在这里看到进步轨迹。")
        return

    for record in records:
        lowest = "、".join(SUBJECT_LABELS[item] for item in record.lowest_subjects)
        score_line = " · ".join(
            f"{SUBJECT_LABELS[key]} {value:.1f}" for key, value in record.scores.items()
        )
        displayed_time = record.created_at.replace("T", " ")[:16]
        st.markdown(
            f"""
            <div class="history-card">
                <strong>{escape(record.student_name)}</strong>
                <span style="color:#64748b"> · {escape(displayed_time)}</span><br>
                <span>{score_line}</span><br>
                <span style="color:#0f766e">总分 {record.overall_band:.1f} · 弱项 {lowest} · 每日 {record.daily_minutes} 分钟</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
