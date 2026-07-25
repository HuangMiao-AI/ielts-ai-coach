"""Local-session Speaking practice with browser recording and no scoring."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.skill_sessions import (
    SkillSession,
    draft_key,
    remaining_seconds,
    start_session,
)


SPEAKING_PARTS = {
    "Part 1": {
        "prompt": "What helps you stay focused when you study?",
        "preparation": 20,
        "response": 45,
    },
    "Part 2": {
        "prompt": (
            "Describe a place where you can study effectively. "
            "Say where it is, what it is like, and why it helps you."
        ),
        "preparation": 60,
        "response": 120,
    },
    "Part 3": {
        "prompt": "How should schools balance quiet study and group discussion?",
        "preparation": 30,
        "response": 90,
    },
}


def _timer_key(user_id: int, part: str, phase: str) -> str:
    """Return a user/part/phase timer key."""

    return f"{draft_key(user_id, 'speaking', part)}_{phase}_timer"


def _render_timer(
    user: User,
    part: str,
    phase: str,
    duration: int,
) -> None:
    """Render one stable preparation or response timer."""

    key = _timer_key(user.id, part, phase)
    session = st.session_state.get(key)
    label = "准备时间" if phase == "preparation" else "回答时间"
    if not isinstance(session, SkillSession):
        if st.button(f"开始{label}", key=f"start_{key}"):
            st.session_state[key] = start_session(
                user_id=user.id,
                skill="speaking",
                task_key=f"{part}-{phase}",
                item_count=1,
                duration_seconds=duration,
            )
            st.rerun()
        return
    seconds = remaining_seconds(session)
    st.metric(label, f"{seconds // 60:02d}:{seconds % 60:02d}")


def _microphone_failure_key(user_id: int) -> str:
    """Return the current user's session-only microphone failure state."""

    return f"speaking_microphone_unavailable_{user_id}"


def _render_microphone_guidance(user: User) -> bool:
    """Render first-use permission guidance and return fallback activation."""

    st.subheader("麦克风测试")
    st.caption("首次使用请先测试麦克风；浏览器会在开始录制时请求权限。")
    guidance_key = f"speaking_microphone_guidance_{user.id}"
    if st.button("麦克风测试", use_container_width=True):
        st.session_state[guidance_key] = True
    if st.session_state.get(guidance_key, False):
        st.info("请点击下方“录制回答”，并在浏览器权限提示中选择允许。")
    failure_key = _microphone_failure_key(user.id)
    if st.button("麦克风无法使用", use_container_width=True):
        st.session_state[failure_key] = True
    if st.session_state.get(failure_key, False):
        st.warning(
            "请在浏览器设置中允许此网站使用麦克风；"
            "也可以使用下方文字回答替代完成练习。"
        )
        return True
    return False


def render_speaking_page(user: User) -> None:
    """Render guided prompts, notes, local recording, and honest completion."""

    st.title("口语练习")
    st.caption("录音仅保存在当前会话，不上传；本功能不提供自动评分。")
    part = st.segmented_control(
        "选择题目部分",
        tuple(SPEAKING_PARTS),
        default="Part 2",
    )
    config = SPEAKING_PARTS[part]
    st.markdown(f"### {config['prompt']}")
    first, second = st.columns(2)
    with first:
        _render_timer(
            user,
            part,
            "preparation",
            int(config["preparation"]),
        )
    with second:
        _render_timer(
            user,
            part,
            "response",
            int(config["response"]),
        )
    use_text_fallback = _render_microphone_guidance(user)

    notes_key = draft_key(user.id, "speaking", f"{part}-notes")
    st.text_area(
        "练习笔记",
        key=notes_key,
        placeholder="只写关键词，不要写完整稿。",
        height=120,
    )
    recording = st.audio_input(
        "录制回答",
        key=f"speaking_recording_{user.id}_{part}",
    )
    if recording is not None:
        st.audio(recording)
        st.caption("录音可在本页回放，离开当前会话后不保证保留。")
    text_response = ""
    if use_text_fallback:
        text_response = st.text_area(
            "文字回答替代",
            key=draft_key(user.id, "speaking", f"{part}-text-response"),
            placeholder="无法录音时，可在这里输入本次回答。",
            height=160,
        )
    completed_key = f"speaking_completed_{user.id}_{part}"
    if st.button(
        "完成本次练习",
        type="primary",
        disabled=recording is None and not text_response.strip(),
        use_container_width=True,
    ):
        st.session_state[completed_key] = (
            "text" if recording is None else "recording"
        )
    completion = st.session_state.get(completed_key)
    if completion == "text":
        st.success("文字回答已完成本次本地练习。未生成分数或能力判断。")
    elif completion == "recording":
        st.success("已完成本地录音与回听。未生成分数或能力判断。")
