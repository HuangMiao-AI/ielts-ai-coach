"""Consolidated user-owned learning and AI history page."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.coaching import get_coach_history
from ielts_ai_coach.services.planning import get_plan_history
from ielts_ai_coach.services.planning_rules import PHASE_LABELS
from ielts_ai_coach.services.reading_practice import list_reading_history
from ielts_ai_coach.services.scores import list_score_history
from ielts_ai_coach.services.tasks import get_study_logs
from ielts_ai_coach.services.writing import (
    get_essay_feedback,
    get_essay_history,
)
from ielts_ai_coach.views.charts import render_score_trend
from ielts_ai_coach.views.writing import render_feedback


def _render_learning_history(user: User) -> None:
    """Render score, plan, and study-time history for one user."""

    scores = list_score_history(user.id)
    plans = get_plan_history(user.id)
    logs = get_study_logs(
        user.id,
        start_date=date.today() - timedelta(days=89),
        end_date=date.today(),
    )
    render_score_trend(scores)
    reading_history = list_reading_history(user.id)
    st.subheader("阅读练习记录")
    if reading_history:
        for item in reading_history:
            with st.expander(
                f"{item.submitted_at:%Y-%m-%d %H:%M} · "
                f"{item.passage_title} · {item.score}/{item.total_questions}"
            ):
                st.write(f"**正确率：** {item.accuracy:.0%}")
                incorrect = ", ".join(item.incorrect_question_ids)
                st.write(f"**错题：** {incorrect or '无'}")
    else:
        st.info("还没有已提交的阅读练习记录。")

    st.subheader("学习时间记录")
    if logs:
        for log in reversed(logs):
            st.write(f"{log.study_date.isoformat()} · {log.minutes}分钟")
    else:
        st.info("还没有已完成任务的学习时间记录。")

    st.subheader("计划版本")
    if plans:
        for plan in plans:
            status = "使用中" if plan.status == "active" else "已归档"
            st.write(
                f"#{plan.id} · {plan.start_date} 至 {plan.end_date} · "
                f"{PHASE_LABELS.get(plan.phase, plan.phase)} · {status}"
            )
    else:
        st.info("还没有生成学习计划。")


def _render_essay_history(user: User) -> None:
    """Render essays and validated reports owned by one user."""

    essays = get_essay_history(user.id)
    if not essays:
        st.info("还没有作文记录。")
        return
    for essay in essays:
        status = "已完成" if essay.status == "completed" else "处理失败"
        with st.expander(
            f"#{essay.id} · {essay.created_at.date()} · {essay.task_type} · "
            f"{essay.word_count}词 · {status}"
        ):
            st.markdown("**题目**")
            st.write(essay.prompt)
            st.markdown("**作文正文**")
            st.write(essay.content)
            feedback = get_essay_feedback(
                user_id=user.id,
                essay_id=essay.id,
            )
            if feedback:
                render_feedback(feedback[0])
            else:
                st.warning("本次批改未完成，可在“写作批改”页面重新尝试。")


def _render_coach_history(user: User) -> None:
    """Render complete coach history owned by one user."""

    messages = get_coach_history(user.id)
    if not messages:
        st.info("还没有AI教练对话记录。")
        return
    for message in reversed(messages):
        sender = "AI教练" if message.role == "assistant" else "我"
        with st.container(border=True):
            st.caption(f"{sender} · {message.created_at:%Y-%m-%d %H:%M}")
            st.write(message.content)


def render_history_page(user: User) -> None:
    """Render all retained records for the authenticated user."""

    st.title("历史记录")
    st.caption("这里仅显示当前账号保存的学习和AI记录。")
    learning_tab, essay_tab, coach_tab = st.tabs(
        ["学习记录", "作文记录", "AI教练对话"]
    )
    with learning_tab:
        _render_learning_history(user)
    with essay_tab:
        _render_essay_history(user)
    with coach_tab:
        _render_coach_history(user)
