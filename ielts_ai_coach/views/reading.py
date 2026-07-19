"""Dedicated Reading library entry and task selection page."""

from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.reading_exam import (
    ReadingExamLibraryItem,
    list_reading_exam_library,
    load_exam_session,
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
        (item for item in items if item.state.task.id == task_id),
        None,
    )


def _open_task(user: User, item: ReadingExamLibraryItem) -> None:
    """Select one user-owned task and initialize its transient session."""

    state = item.state
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
    """Render available active-plan Reading tasks."""

    st.title("阅读练习")
    st.caption("原创 IELTS 风格练习，非官方 IELTS 或 Cambridge 试题。")
    if not items:
        st.info("当前学习计划中没有可用的阅读练习，请先生成学习计划。")
        return
    st.subheader("练习题库")
    for item in items:
        state = item.state
        with st.container(border=True):
            status = "已提交" if item.is_submitted else "待完成"
            st.markdown(f"### {state.passage.title}")
            st.caption(
                f"{state.task.task_date} · 约 {state.passage.word_count} 词 · "
                f"{len(state.passage.questions)} 题 · {status}"
            )
            saved = st.session_state.get(
                f"reading_exam_{user.id}_{state.task.id}"
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
                key=f"reading_library_open_{state.task.id}",
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
    render_reading_session(
        user,
        selected.state,
        selected_key=selected_reading_task_key(user.id),
    )
