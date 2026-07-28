"""Formal Listening start and sound-check flow outside the active exam page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import clear_exam_control, load_exam_control
from ielts_ai_coach.services.listening_bank import ListeningTest
from ielts_ai_coach.services.listening_session import (
    listening_answer_key,
    listening_audio_command_key,
    listening_audio_state_key,
    listening_confirmation_key,
    listening_result_key,
    listening_session_key,
    request_listening_audio_command,
    selected_test_key,
)
from ielts_ai_coach.services.skill_sessions import start_session
from ielts_ai_coach.views.listening_audio import render_sound_check


def render_listening_formal_start(user: User, test: ListeningTest) -> None:
    """Require a sound check and explicit confirmation before official timing."""

    st.title("正式开始听力练习")
    st.caption(f"{test.title} · {len(test.questions)} 题 · 约 {test.estimated_minutes} 分钟")
    st.info("请先完成声音测试。正式开始后，计时器和正式音频将同时启用。")
    render_sound_check(user, test)
    back, start = st.columns(2)
    if back.button("返回听力题库", use_container_width=True):
        st.session_state.pop(selected_test_key(user.id), None)
        st.rerun()
    if start.button("开始正式练习", type="primary", use_container_width=True):
        reset_listening_attempt(user, test)
        session = start_session(
            session=None,
            user_id=user.id,
            skill="listening",
            task_key=test.test_id,
            item_count=len(test.questions),
            duration_seconds=test.estimated_minutes * 60,
        )
        st.session_state[listening_session_key(user.id, test.test_id)] = session
        load_exam_control(
            st.session_state,
            user_id=user.id,
            skill="listening",
            task_key=test.test_id,
            duration_seconds=session.duration_seconds,
            now=session.started_at,
        )
        request_listening_audio_command(st.session_state, user.id, test.test_id, "play")
        st.rerun()


def reset_listening_attempt(user: User, test: ListeningTest) -> None:
    """Clear only this user's transient test state before a fresh formal start."""

    for key in (
        listening_answer_key(user.id, test.test_id),
        listening_audio_command_key(user.id, test.test_id),
        listening_audio_state_key(user.id, test.test_id),
        listening_confirmation_key(user.id, test.test_id),
        listening_result_key(user.id, test.test_id),
        listening_session_key(user.id, test.test_id),
    ):
        st.session_state.pop(key, None)
    clear_exam_control(st.session_state, user_id=user.id, skill="listening", task_key=test.test_id)
