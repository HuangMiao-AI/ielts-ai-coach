"""Session-only Reading library and bilingual results for guests."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.auth import GuestIdentity
from ielts_ai_coach.services.question_bank import get_reading_passage, load_reading_catalog
from ielts_ai_coach.services.reading_scoring import ReadingScore, score_reading_answers
from ielts_ai_coach.views.review_components import render_reading_review
from ielts_ai_coach.views.task_cards import (
    render_reading_exam_question,
    render_reading_passage,
)


def render_guest_reading_page(guest: GuestIdentity) -> None:
    """Offer original Reading practice without durable plans or attempts."""

    selected_key = f"guest_reading_selected_{guest.id}"
    passage_id = st.session_state.get(selected_key)
    if not isinstance(passage_id, str):
        st.title("阅读练习")
        st.caption("项目原创文章 · 游客答案与结果仅保存在当前会话。")
        for passage in load_reading_catalog():
            with st.container(border=True):
                st.subheader(passage.title)
                st.caption(
                    f"{passage.topic} · 约 {passage.word_count} 词 · "
                    f"{len(passage.questions)} 题"
                )
                if st.button(
                    "开始练习",
                    key=f"guest_open_{passage.passage_id}",
                    use_container_width=True,
                ):
                    st.session_state[selected_key] = passage.passage_id
                    st.rerun()
        return

    passage = get_reading_passage(passage_id)
    result_key = f"guest_reading_result_{guest.id}_{passage_id}"
    result = st.session_state.get(result_key)
    if isinstance(result, ReadingScore):
        st.title("阅读练习")
        st.caption("本次结果仅保存在当前会话。")
        render_reading_review(result, passage)
        if st.button("返回文章库", use_container_width=True):
            st.session_state.pop(selected_key, None)
            st.rerun()
        return

    if st.button("返回文章库"):
        st.session_state.pop(selected_key, None)
        st.rerun()
    render_reading_passage(passage)
    answers: dict[str, str] = {}
    st.subheader("问题")
    for index, question in enumerate(passage.questions, start=1):
        answer = render_reading_exam_question(
            question,
            index=index,
            total=len(passage.questions),
            widget_key=f"guest_reading_{guest.id}_{question.question_id}",
        )
        if answer:
            answers[question.question_id] = answer
    remaining = len(passage.questions) - len(answers)
    st.caption(f"已答 {len(answers)}/{len(passage.questions)} · 未答 {remaining}")
    if st.button(
        "提交并查看双语解析",
        type="primary",
        disabled=remaining > 0,
        use_container_width=True,
    ):
        st.session_state[result_key] = score_reading_answers(passage, answers)
        st.rerun()
