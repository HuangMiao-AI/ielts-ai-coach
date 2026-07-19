"""Honest Listening Demo practice without bundled copyrighted audio."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.skill_sessions import (
    SkillSession,
    draft_key,
    move_item,
    remaining_seconds,
    start_session,
)


LISTENING_DEMOS = {
    "Section 1": (
        "记录来电者姓名",
        "记录预约日期",
        "记录联系电话",
    ),
    "Section 2": (
        "识别场所入口",
        "记录开放时间",
        "总结参观规则",
    ),
    "Section 3": (
        "识别两位学生的观点",
        "记录导师建议",
        "总结下一步行动",
    ),
    "Section 4": (
        "记录讲座主题",
        "提取两个研究发现",
        "写下结论关键词",
    ),
}


def _session_key(user_id: int, section: str) -> str:
    """Return one user/section Listening session key."""

    return f"{draft_key(user_id, 'listening', section)}_session"


def _render_demo(
    user: User,
    section: str,
    session: SkillSession,
) -> None:
    """Render one guided Demo section with transient answers."""

    prompts = LISTENING_DEMOS[section]
    minutes, seconds = divmod(remaining_seconds(session), 60)
    st.caption(
        f"Demo · 剩余时间 {minutes:02d}:{seconds:02d} · "
        f"进度 {session.current_index + 1}/{session.item_count}"
    )
    st.progress(session.progress)
    st.info("请播放你合法拥有的练习音频；本项目不附带版权音频。")
    answer_key = draft_key(user.id, "listening", section)
    answers = st.session_state.get(answer_key, {})
    if not isinstance(answers, dict):
        answers = {}
    prompt = prompts[session.current_index]
    answer = st.text_input(
        f"第 {session.current_index + 1} 项：{prompt}",
        value=str(answers.get(str(session.current_index), "")),
        key=f"listening_answer_{user.id}_{section}_{session.current_index}",
    )
    answers[str(session.current_index)] = answer
    st.session_state[answer_key] = answers

    previous, next_column = st.columns(2)
    session_key = _session_key(user.id, section)
    if previous.button(
        "上一项",
        disabled=session.current_index == 0,
        use_container_width=True,
    ):
        st.session_state[session_key] = move_item(session, -1)
        st.rerun()
    if session.current_index < session.item_count - 1:
        if next_column.button("下一项", use_container_width=True):
            st.session_state[session_key] = move_item(session, 1)
            st.rerun()
    elif next_column.button(
        "完成练习",
        type="primary",
        use_container_width=True,
    ):
        st.session_state[f"{session_key}_confirm"] = True

    if st.session_state.get(f"{session_key}_confirm", False):
        st.warning("请确认已完成自查。Demo 结果不保存分数。")
        if st.button("确认完成", type="primary", use_container_width=True):
            st.session_state[f"{session_key}_completed"] = True
            st.session_state[f"{session_key}_confirm"] = False
            st.rerun()
    if st.session_state.get(f"{session_key}_completed", False):
        st.success("Demo 已完成。答案仅保存在当前会话，不保存分数。")


def render_listening_page(user: User) -> None:
    """Render a local guided Listening Demo with honest capability copy."""

    st.title("听力练习")
    st.caption("Demo 模式：练习流程与记录，不保存分数。")
    section = st.selectbox("选择练习", tuple(LISTENING_DEMOS))
    session_key = _session_key(user.id, section)
    session = st.session_state.get(session_key)
    if not isinstance(session, SkillSession):
        st.write("选择你合法拥有的音频，按提示完成定位和记录。")
        if st.button("开始 Demo", type="primary", use_container_width=True):
            st.session_state[session_key] = start_session(
                user_id=user.id,
                skill="listening",
                task_key=section,
                item_count=len(LISTENING_DEMOS[section]),
                duration_seconds=1800,
            )
            st.rerun()
        return
    _render_demo(user, section, session)
