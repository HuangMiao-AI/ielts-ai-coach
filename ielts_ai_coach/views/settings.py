"""Simplified Chinese account settings and user-data controls."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from ielts_ai_coach.auth import logout
from ielts_ai_coach.database.data_repository import DeletionCounts
from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.data_management import (
    clear_ai_content,
    clear_learning_records,
)
from ielts_ai_coach.views.learner_profile_form import (
    render_learning_profile_editor,
)


def _render_confirmation(
    *,
    user: User,
    state_key: str,
    title: str,
    description: str,
    final_label: str,
    action: Callable[[int], DeletionCounts],
) -> None:
    """Render a two-step destructive-action confirmation."""

    st.subheader(title)
    st.write(description)
    if st.button("开始清理", key=f"{state_key}_start"):
        st.session_state[state_key] = True

    if not st.session_state.get(state_key):
        return
    st.warning("此操作无法撤销，请再次确认。")
    confirmation = st.checkbox(
        f"我确认只清理账号“{user.username}”的数据",
        key=f"{state_key}_checkbox",
    )
    left, right = st.columns(2)
    if left.button(
        final_label,
        type="primary",
        disabled=not confirmation,
        key=f"{state_key}_confirm",
    ):
        action(user.id)
        st.session_state[state_key] = False
        st.success("清理完成。")
    if right.button("取消", key=f"{state_key}_cancel"):
        st.session_state[state_key] = False
        st.rerun()


def render_settings_page(user: User) -> None:
    """Render username, logout, and user-owned data deletion controls."""

    st.title("设置")
    st.caption("管理当前登录账号及其保存的数据。")
    st.text_input("当前用户名", value=user.username, disabled=True)
    if st.button("退出登录", use_container_width=True, key="settings_logout"):
        logout()
        st.rerun()

    st.divider()
    st.subheader("学习设置")
    st.caption("更新目标、学习时间和可选当前成绩。")
    render_learning_profile_editor(user, source_key="settings")

    st.divider()
    with st.expander("清理学习记录"):
        _render_confirmation(
            user=user,
            state_key="confirm_learning_delete",
            title="删除自己的学习记录",
            description=(
                "将删除当前账号的成绩、学习计划、任务和学习时长。"
                "学生档案和账号会保留。"
            ),
            final_label="确认删除学习记录",
            action=clear_learning_records,
        )
    with st.expander("清理作文和AI对话"):
        _render_confirmation(
            user=user,
            state_key="confirm_ai_delete",
            title="删除自己的作文和AI对话",
            description=(
                "将删除当前账号的作文、写作反馈和AI教练消息。"
                "当天额度计数会保留，避免重复使用额度。"
            ),
            final_label="确认删除作文和AI对话",
            action=clear_ai_content,
        )

    st.info("V1暂不支持用户自行删除账号。")
