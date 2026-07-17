"""Responsive authenticated dashboard for IELTS AI Coach."""

from __future__ import annotations

from typing import Mapping

import streamlit as st

from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.database.models import StudentProfile, User
from ielts_ai_coach.services.coaching import get_coach_remaining
from ielts_ai_coach.services.profiles import days_until_exam, get_profile
from ielts_ai_coach.services.scoring import SUBJECT_LABELS, analyze_scores
from ielts_ai_coach.services.scores import get_latest_score, list_score_history
from ielts_ai_coach.services.task_content import get_task_content
from ielts_ai_coach.services.tasks import get_tasks_for_day, get_week_progress
from ielts_ai_coach.services.writing import get_writing_remaining
from ielts_ai_coach.views.charts import render_score_trend


def _section(title: str) -> None:
    """Render a consistent dashboard section heading."""

    st.markdown(
        f'<div class="section-heading">{title}</div>',
        unsafe_allow_html=True,
    )


def _render_core_entries(page_refs: Mapping[str, object] | None) -> None:
    """Render the four primary student actions as large page links."""

    _section("快捷开始")
    entries = (
        ("today", "今日任务", "✅"),
        ("plan", "七天计划", "🗓️"),
        ("coach", "AI教练", "💬"),
        ("writing", "写作批改", "✍️"),
    )
    if not page_refs:
        st.caption("今日任务 · 七天计划 · AI教练 · 写作批改")
        return
    columns = st.columns(4)
    for column, (key, label, icon) in zip(columns, entries):
        with column:
            st.page_link(
                page_refs[key],
                label=label,
                icon=icon,
                use_container_width=True,
            )


def _render_today_progress(user: User) -> list:
    """Render today's completion ratio and return the task list."""

    tasks = get_tasks_for_day(user.id)
    completed = sum(task.status == "completed" for task in tasks)
    _section("今日学习进度")
    if not tasks:
        st.metric("今日完成", "待生成计划")
        st.info("生成七天计划后，这里会显示今天的学习进度。")
        return tasks
    st.metric("今日完成", f"{completed}/{len(tasks)} 项")
    st.progress(
        completed / len(tasks),
        text=f"已完成 {completed} 项，共 {len(tasks)} 项",
    )
    return tasks


def _render_target(profile: StudentProfile) -> None:
    """Render the target band and exam countdown."""

    _section("当前目标")
    target_column, countdown_column = st.columns(2)
    target_column.metric("目标IELTS分数", f"{profile.target_overall:.1f}")
    countdown_column.metric("距离考试", f"{days_until_exam(profile)} 天")


def _render_today_tasks(tasks: list) -> None:
    """Render concrete titles and completion criteria for today."""

    _section("今日任务")
    if not tasks:
        st.caption("暂无今日任务。")
        return
    for task in tasks:
        content = get_task_content(task)
        status = "✅" if task.status == "completed" else "⬜"
        with st.container(border=True):
            st.markdown(f"{status} **{content.task_title}**")
            st.markdown(
                f'<span class="task-time-badge">'
                f"计划 {task.planned_minutes} 分钟</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"完成标准：{content.completion_criteria}")


def _render_latest_score(user: User, profile: StudentProfile) -> None:
    """Render latest section scores, weakness, and recent trend."""

    latest_score = get_latest_score(user.id)
    _section("最新成绩")
    if latest_score is None:
        st.info("下一步：进入“成绩诊断”录入最近一次IELTS四科成绩。")
        return
    scores = {
        "listening": latest_score.listening,
        "reading": latest_score.reading,
        "writing": latest_score.writing,
        "speaking": latest_score.speaking,
    }
    st.metric("最新总分", f"{latest_score.overall:.1f}")
    columns = st.columns(4)
    for column, subject in zip(columns, scores):
        column.metric(SUBJECT_LABELS[subject], f"{scores[subject]:.1f}")
    diagnosis = analyze_scores(scores, profile.target_overall)
    weak_labels = "、".join(
        SUBJECT_LABELS[subject] for subject in diagnosis.lowest_subjects
    )
    st.warning(f"当前弱项：{weak_labels}。计划会优先分配对应训练。")
    render_score_trend(
        list_score_history(user.id, limit=8),
        title="最近成绩趋势",
    )


def _render_week_statistics(user: User) -> None:
    """Render weekly study time and completion rate."""

    progress = get_week_progress(user.id)
    _section("本周学习统计")
    time_column, rate_column = st.columns(2)
    time_column.metric("本周学习时间", f"{progress.actual_minutes} 分钟")
    rate_column.metric(
        "本周任务完成率",
        f"{progress.completion_rate * 100:.0f}%",
    )


def _render_ai_quota(user: User) -> None:
    """Render today's coach and writing allowance."""

    _section("AI剩余额度")
    coach_column, writing_column = st.columns(2)
    coach_column.metric("AI教练剩余", f"{get_coach_remaining(user.id)}/20 条")
    writing_column.metric(
        "写作批改剩余",
        f"{get_writing_remaining(user.id)}/3 次",
    )
    if get_ai_provider().is_mock:
        st.caption("当前为演示模式；配置Qwen API Key后可启用真实AI服务。")


def render_dashboard(
    user: User,
    page_refs: Mapping[str, object] | None = None,
) -> None:
    """Render the mobile-first user-owned study overview."""

    profile = get_profile(user.id)
    display_name = profile.nickname if profile else user.username
    st.title(f"你好，{display_name}")
    st.caption("今天也向目标前进一步。")
    _render_core_entries(page_refs)
    tasks = _render_today_progress(user)

    if profile is None:
        st.info(
            "欢迎使用 IELTS AI Coach。请先打开“我的档案”，设置目标分、"
            "考试日期和每日学习时间。"
        )
        _render_ai_quota(user)
        return

    _render_target(profile)
    _render_today_tasks(tasks)
    _render_latest_score(user, profile)
    _render_week_statistics(user)
    _render_ai_quota(user)
