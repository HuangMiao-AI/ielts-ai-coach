"""Simplified Chinese AI study coach page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.coaching import (
    COACH_DAILY_LIMIT,
    CoachServiceError,
    clear_current_conversation,
    get_coach_remaining,
    get_visible_messages,
    send_coach_message,
)


COACH_ERRORS = {
    "invalid_message": "请输入1–1000个字符的问题。",
    "quota_exhausted": "今天的AI教练额度已用完，请明天再来。",
    "network_unavailable": "AI服务暂时无法连接，请稍后重试。",
    "request_failed": "AI请求失败，请稍后重试。",
    "provider_rejected_request": "AI服务暂时无法处理该问题，请换一种问法。",
    "invalid_provider_response": "AI返回内容异常，请稍后重试。",
    "empty_provider_response": "AI没有返回有效内容，请稍后重试。",
}


def render_coach_page(user: User) -> None:
    """Render one user's saved coach conversation and quota."""

    provider = get_ai_provider()
    remaining = get_coach_remaining(user.id)
    st.title("AI学习教练")
    st.caption("结合你的目标、弱项、当前计划和近期完成情况给出学习建议。")

    if provider.is_mock:
        st.info(
            "当前为演示模式：未配置Qwen API Key，回答由本地Mock生成，不会发送网络请求。",
            icon="🧪",
        )

    quota_column, action_column = st.columns([3, 1])
    quota_column.metric(
        "今日剩余额度",
        f"{remaining}/{COACH_DAILY_LIMIT} 条",
    )
    if action_column.button(
        "清空当前对话",
        use_container_width=True,
        disabled=not get_visible_messages(user.id),
    ):
        clear_current_conversation(user.id)
        st.rerun()

    messages = get_visible_messages(user.id)
    if not messages:
        st.markdown(
            '<div class="empty-card">可以问：如何提高写作？今天应该先完成哪项任务？'
            "如何复盘阅读错题？</div>",
            unsafe_allow_html=True,
        )
    for message in messages:
        role = "assistant" if message.role == "assistant" else "user"
        with st.chat_message(role):
            st.write(message.content)

    question = st.chat_input(
        "输入你的IELTS学习问题",
        max_chars=1000,
        disabled=remaining <= 0,
    )
    if not question:
        return

    with st.chat_message("user"):
        st.write(question)
    try:
        with st.spinner("AI教练正在思考..."):
            reply = send_coach_message(
                user_id=user.id,
                content=question,
                provider=provider,
            )
    except CoachServiceError as error:
        st.error(COACH_ERRORS.get(str(error), "AI服务暂时不可用，请稍后重试。"))
    else:
        with st.chat_message("assistant"):
            st.write(reply.message.content)
        st.rerun()

    st.caption("AI建议仅供学习参考，不替代正式教师指导或官方评分。")
