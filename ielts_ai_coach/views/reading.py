"""Dedicated Reading library entry and task selection page."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.reading_exam import (
    ReadingExamLibraryItem,
    list_reading_exam_library,
    load_exam_session,
    open_reading_library_item,
)
from ielts_ai_coach.views.reading_workspace import render_reading_session


def selected_reading_task_key(user_id: int) -> str:
    """Return the user-scoped selected Reading task key."""

    return f"reading_selected_task_{user_id}"


def _find_selected(
    items: tuple[ReadingExamLibraryItem, ...],
    task_id: object,
) -> ReadingExamLibraryItem | None:
    """Resolve a selected item from the current user-owned library."""

    return next(
        (
            item
            for item in items
            if item.state is not None and item.state.task.id == task_id
        ),
        None,
    )


def _open_task(user: User, item: ReadingExamLibraryItem) -> None:
    """Select one user-owned task and initialize its transient session."""

    state = item.state or open_reading_library_item(
        user_id=user.id,
        passage_id=item.passage.passage_id,
    )
    st.session_state[selected_reading_task_key(user.id)] = state.task.id
    if not item.is_submitted:
        load_exam_session(
            st.session_state,
            user_id=user.id,
            task_id=state.task.id,
            question_ids=tuple(
                question.question_id for question in state.passage.questions
            ),
        )
    st.rerun()


def _render_library(
    user: User,
    items: tuple[ReadingExamLibraryItem, ...],
) -> None:
    """Render the complete original Reading catalog."""

    st.title("阅读练习")
    st.caption("原创 IELTS 风格练习，非官方 IELTS 或 Cambridge 试题。")
    st.subheader("练习题库")
    for item in items:
        state = item.state
        passage = item.passage
        with st.container(border=True):
            status = {
                "submitted": "已提交",
                "started": "进行中",
                "not_started": "未开始",
            }[item.status]
            st.markdown(f"### {passage.title}")
            st.caption(
                f"{passage.topic} · 约 {passage.word_count} 词 · "
                f"{len(passage.questions)} 题 · 约 30 分钟 · {status}"
            )
            saved = (
                st.session_state.get(
                    f"reading_exam_{user.id}_{state.task.id}"
                )
                if state is not None
                else None
            )
            label = (
                "查看结果"
                if item.is_submitted
                else "继续练习"
                if saved is not None
                else "开始练习"
            )
            if st.button(
                label,
                key=f"reading_library_open_{passage.passage_id}",
                type="primary" if not item.is_submitted else "secondary",
                use_container_width=True,
            ):
                _open_task(user, item)


def render_reading_page(
    user: User,
    page_refs: Mapping[str, st.Page],
) -> None:
    """Render the complete user-owned Reading practice loop."""

    del page_refs
    items = list_reading_exam_library(user.id)
    selected = _find_selected(
        items,
        st.session_state.get(selected_reading_task_key(user.id)),
    )
    if selected is None:
        _render_library(user, items)
        return
    if selected.state is None:
        st.session_state.pop(selected_reading_task_key(user.id), None)
        st.rerun()
        return
    render_reading_session(
        user,
        selected.state,
        selected_key=selected_reading_task_key(user.id),
    )
