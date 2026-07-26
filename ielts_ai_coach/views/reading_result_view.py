"""Persisted Reading result stage and return-to-library flow."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import clear_exam_control
from ielts_ai_coach.services.reading_exam import clear_exam_session
from ielts_ai_coach.services.reading_practice import ReadingPracticeState
from ielts_ai_coach.views.task_cards import (
    render_reading_result,
    render_reading_result_summary,
)


def render_reading_session_result(
    user: User,
    state: ReadingPracticeState,
    selected_key: str,
) -> None:
    """Render one persisted result and optional complete review."""

    assert state.score is not None
    st.title("阅读练习结果")
    st.success("评分、任务完成状态和学习日志已同步保存。")
    render_reading_result_summary(state.score)
    review_key = f"reading_review_open_{user.id}_{state.task.id}"
    if not st.session_state.get(review_key, False):
        if st.button("查看逐题解析", type="primary", use_container_width=True):
            st.session_state[review_key] = True
            st.rerun()
    else:
        render_reading_result(state.score)
    if st.button("返回题库", key="reading_result_back"):
        st.session_state.pop(selected_key, None)
        clear_exam_session(
            st.session_state,
            user_id=user.id,
            task_id=state.task.id,
        )
        clear_exam_control(
            st.session_state,
            user_id=user.id,
            skill="reading",
            task_key=str(state.task.id),
        )
        st.rerun()
