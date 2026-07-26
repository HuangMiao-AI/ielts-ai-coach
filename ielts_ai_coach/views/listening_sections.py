"""Listening library and deterministic result sections."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import load_exam_control
from ielts_ai_coach.services.listening_bank import (
    ListeningTest,
    load_listening_bank,
)
from ielts_ai_coach.services.listening_scoring import ListeningScore
from ielts_ai_coach.services.listening_session import (
    listening_result_key,
    listening_session_key,
    selected_test_key,
)
from ielts_ai_coach.services.skill_sessions import SkillSession, start_session


def render_listening_library(user: User) -> None:
    """Render both bundled original mini tests."""

    bank = load_listening_bank()
    st.title("听力练习")
    st.caption(bank.copyright_notice)
    st.info("音频、题目和评分均在本地运行；本阶段结果仅保存在当前会话。")
    for index, test in enumerate(bank.tests, start=1):
        with st.container(border=True):
            st.markdown(f"### Test {index} · {test.title}")
            st.caption(
                f"2 Sections · {len(test.questions)} 题 · "
                f"约 {test.estimated_minutes} 分钟 · 本地 WAV 音频"
            )
            result = st.session_state.get(
                listening_result_key(user.id, test.test_id)
            )
            if isinstance(result, ListeningScore):
                st.success(
                    f"本次会话已完成：{result.correct_count}/"
                    f"{result.total_questions}"
                )
            if not st.button(
                f"开始 Test {index}",
                key=f"listening_start_{user.id}_{test.test_id}",
                type="primary",
                use_container_width=True,
            ):
                continue
            st.session_state[selected_test_key(user.id)] = test.test_id
            session_key = listening_session_key(user.id, test.test_id)
            saved = st.session_state.get(session_key)
            session = start_session(
                session=saved if isinstance(saved, SkillSession) else None,
                user_id=user.id,
                skill="listening",
                task_key=test.test_id,
                item_count=len(test.questions),
                duration_seconds=test.estimated_minutes * 60,
            )
            st.session_state[session_key] = session
            load_exam_control(
                st.session_state,
                user_id=user.id,
                skill="listening",
                task_key=test.test_id,
                duration_seconds=session.duration_seconds,
                now=session.started_at,
            )
            st.rerun()


def render_listening_result(
    user: User,
    test: ListeningTest,
    score: ListeningScore,
) -> None:
    """Render session-only deterministic score and full review."""

    st.title("听力练习结果")
    st.caption("结果仅保存在当前会话，不写入数据库或学习分析。")
    total, accuracy = st.columns(2)
    total.metric("总分", f"{score.correct_count}/{score.total_questions}")
    accuracy.metric("正确率", f"{score.accuracy:.0%}")
    for index, result in enumerate(score.results, start=1):
        marker = "✅" if result.is_correct else "❌"
        with st.container(border=True):
            st.markdown(f"### {marker} 第 {index} 题")
            st.write(result.question)
            st.markdown(f"**你的答案：** {result.user_answer or '未作答'}")
            st.markdown(f"**正确答案：** {result.correct_answer}")
            st.markdown(f"**解析：** {result.explanation}")
            st.markdown(f"**音频证据：** {result.evidence}")
    if st.button("返回听力题库", use_container_width=True):
        st.session_state.pop(selected_test_key(user.id), None)
        st.rerun()
