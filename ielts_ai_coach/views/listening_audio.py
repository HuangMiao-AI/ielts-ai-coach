"""Controller-owned HTML5 audio rendering for Listening practice."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import ExamSession, ExamStatus
from ielts_ai_coach.services.listening_bank import ListeningTest
from ielts_ai_coach.services.listening_session import (
    get_listening_audio_command,
    listening_audio_state_key,
    record_listening_audio_state,
)
from ielts_ai_coach.ui.exam_audio import (
    AudioPlaybackState,
    render_exam_audio,
    static_audio_url,
)


def render_sound_check(user: User, test: ListeningTest) -> None:
    """Render an untimed local audio check before the official session starts."""

    st.subheader("声音测试")
    st.caption("请先点击播放音频，确认可以听清。此步骤不会启动正式计时。")
    state = render_exam_audio(
        audio_url=static_audio_url(test.audio_path),
        command="load",
        command_id=0,
        locked=False,
        key=f"listening_sound_check_{user.id}_{test.test_id}",
    )
    _render_audio_error(state)


def render_controlled_listening_audio(
    user: User,
    test: ListeningTest,
    control: ExamSession,
) -> AudioPlaybackState:
    """Render the only official player and retain its latest exact position."""

    command, command_id = get_listening_audio_command(
        st.session_state,
        user.id,
        test.test_id,
    )
    saved = st.session_state.get(listening_audio_state_key(user.id, test.test_id))
    seek_seconds = (
        float(saved.get("current_time", 0.0))
        if isinstance(saved, dict) and command in {"resume", "seek_to"}
        else None
    )
    state = render_exam_audio(
        audio_url=static_audio_url(test.audio_path),
        command=command,
        command_id=command_id,
        locked=control.status is not ExamStatus.RUNNING,
        seek_seconds=seek_seconds,
        key=f"listening_exam_audio_{user.id}_{test.test_id}",
    )
    record_listening_audio_state(st.session_state, user.id, test.test_id, state)
    _render_audio_error(state)
    return state


def render_listening_toolbar(
    test: ListeningTest,
    *,
    question_number: int,
    section_title: str,
    answered: int,
    state: AudioPlaybackState,
) -> None:
    """Show Listening progress and real player state without a second timer."""

    columns = st.columns(4)
    columns[0].metric("当前进度", f"{question_number}/{len(test.questions)}")
    columns[1].metric("当前分段", section_title)
    columns[2].metric("已答题数", f"{answered}/{len(test.questions)}")
    columns[3].metric("音频状态", _audio_label(state))


def _audio_label(state: AudioPlaybackState) -> str:
    """Translate a verified browser state without claiming false success."""

    return {
        "idle": "等待播放",
        "loading": "载入中",
        "playing": "播放中",
        "paused": "已暂停",
        "ended": "播放结束",
        "error": "播放失败",
    }[state.playback_state]


def _render_audio_error(state: AudioPlaybackState) -> None:
    """Expose autoplay and media failures instead of silently faking playback."""

    if state.error:
        st.error(f"音频未能自动播放：{state.error} 请点击播放器中的“播放音频”。")
