"""Listening library and deterministic result sections."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.listening_bank import (
    ListeningTest,
    load_listening_bank,
)
from ielts_ai_coach.services.listening_scoring import ListeningScore
from ielts_ai_coach.services.listening_session import (
    listening_result_key,
    selected_test_key,
)
from ielts_ai_coach.views.review_components import render_listening_review


def render_listening_library(user: User) -> None:
    """Render both bundled original mini tests."""

    bank = load_listening_bank()
    st.title("听力练习")
    st.caption(bank.copyright_notice)
    st.info("音频、题目和评分均在本地运行；本阶段结果仅保存在当前会话。")
    for index, test in enumerate(bank.tests, start=1):
        with st.container(border=True):
            st.markdown(f"### {test.title}")
            st.caption(
                f"原创 Listening Mini Practice · 2 个短场景 · "
                f"{len(test.questions)} 题 · 建议 {test.estimated_minutes} 分钟 · "
                "本地 WAV 开发用合成音频"
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
                f"开始 Mini Practice {index}",
                key=f"listening_start_{user.id}_{test.test_id}",
                type="primary",
                use_container_width=True,
            ):
                continue
            st.session_state[selected_test_key(user.id)] = test.test_id
            st.rerun()


def render_listening_result(
    user: User,
    test: ListeningTest,
    score: ListeningScore,
) -> None:
    """Render session-only deterministic score and full review."""

    st.title("听力练习结果")
    st.caption("结果仅保存在当前会话，不写入数据库或学习分析。")
    render_listening_review(score, test)
    if st.button("返回听力题库", use_container_width=True):
        st.session_state.pop(selected_test_key(user.id), None)
        st.rerun()
