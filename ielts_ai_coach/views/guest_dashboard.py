"""Database-free dashboard for one transient guest session."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from ielts_ai_coach.auth import GuestIdentity
from ielts_ai_coach.views.score_chip import render_score_chip


def render_guest_dashboard(
    guest: GuestIdentity,
    page_refs: Mapping[str, st.Page],
) -> None:
    """Render guest-safe entries without reading or writing user records."""

    heading, score = st.columns((4, 1))
    with heading:
        st.title("IELTS AI Coach")
        st.caption("先体验，再决定是否登录保存长期学习记录。")
    with score:
        render_score_chip(guest.id)

    with st.container(key="training_arena_entry", border=True):
        st.markdown("## IELTS 训练场")
        st.caption("IELTS Training Arena · 5题一局，快速练习雅思核心能力。")
        st.page_link(
            page_refs["arena"],
            label="开始一局",
            icon=":material/play_arrow:",
            use_container_width=True,
        )

    st.markdown('<div class="section-heading">快捷开始</div>', unsafe_allow_html=True)
    entries = (
        ("reading", "阅读", "8 篇项目原创文章与双语解析"),
        ("listening", "听力", "核心词汇 · 听发音 · 练拼写"),
        ("writing", "写作", "Academic Task 1 视觉题与 Task 2"),
    )
    columns = st.columns(3)
    for column, (key, label, detail) in zip(columns, entries):
        with column:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.caption(detail)
                st.page_link(
                    page_refs[key],
                    label=f"开始{label}练习",
                    use_container_width=True,
                )
    st.info("游客练习数据只保留在当前会话中，不会写入长期学习记录。")
