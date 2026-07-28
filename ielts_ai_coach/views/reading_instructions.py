"""Reading formal-start instructions separated from the all-question workspace."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import load_exam_control
from ielts_ai_coach.services.exam_state import start_exam
from ielts_ai_coach.services.reading_exam import load_exam_session, save_exam_session
from ielts_ai_coach.services.reading_practice import ReadingPracticeState


def reading_question_ids(state: ReadingPracticeState) -> tuple[str, ...]:
    """Return stable question identifiers for one selected Reading practice."""

    return tuple(question.question_id for question in state.passage.questions)


def render_reading_instructions(
    user: User,
    state: ReadingPracticeState,
    selected_key: str,
) -> None:
    """Render rules before the stable Reading exam timer begins."""

    st.title(state.passage.title)
    st.subheader("考试说明")
    st.write(
        f"本练习共 {len(state.passage.questions)} 题，推荐时间：{state.passage.recommended_minutes} 分钟。"
    )
    st.write("提交前不会显示正确答案或解析；确认提交后答案将无法修改。")
    st.caption("草稿只保存在当前浏览器会话中，关闭会话后可能无法恢复。")
    back, start = st.columns(2)
    if back.button("返回题库", use_container_width=True):
        st.session_state.pop(selected_key, None)
        st.rerun()
    if start.button("开始计时练习", type="primary", use_container_width=True):
        session = load_exam_session(
            st.session_state,
            user_id=user.id,
            task_id=state.task.id,
            question_ids=reading_question_ids(state),
            duration_seconds=state.passage.recommended_minutes * 60,
        )
        session = start_exam(session)
        save_exam_session(st.session_state, session)
        load_exam_control(
            st.session_state,
            user_id=user.id,
            skill="reading",
            task_key=str(state.task.id),
            duration_seconds=session.duration_seconds,
            now=session.started_at,
        )
        st.rerun()
