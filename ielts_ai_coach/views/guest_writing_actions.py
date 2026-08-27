"""Database-free completion controls for guest Writing practice."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.auth import GuestIdentity
from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    cancel_submission,
    clear_exam_control,
    mark_submitted,
    request_submission,
    save_exam_control,
)
from ielts_ai_coach.services.writing_tasks import inspect_writing_locally
from ielts_ai_coach.views.writing_actions import WritingDraftKeys


def _save(guest: GuestIdentity, task_key: str, control: ExamSession) -> None:
    """Persist one guest controller only in the active session."""

    save_exam_control(
        st.session_state,
        user_id=guest.id,
        task_key=task_key,
        session=control,
    )


def render_guest_writing_actions(
    *,
    guest: GuestIdentity,
    content: str,
    minimum_words: int,
    control: ExamSession | None,
    control_task_key: str,
    keys: WritingDraftKeys,
) -> None:
    """Complete a guest draft once while keeping every value in session state."""

    result_key = f"guest_writing_result_{guest.id}_{control_task_key}"
    result = st.session_state.get(result_key)
    if isinstance(result, dict):
        st.success("本次写作已完成；结果仅保存在当前会话。")
        columns = st.columns(3)
        columns[0].metric("字数", result["word_count"])
        columns[1].metric("段落", result["paragraph_count"])
        columns[2].metric("建议字数", "已达到" if result["meets_length"] else "未达到")
        return

    clear_column, finish_column = st.columns(2)
    if clear_column.button("清空草稿", use_container_width=True):
        st.session_state[keys.clear] = True
    if finish_column.button(
        "完成本次练习",
        type="primary",
        disabled=(
            control is None
            or control.status not in {ExamStatus.RUNNING, ExamStatus.TIMED_OUT}
        ),
        use_container_width=True,
    ):
        assert control is not None
        control = request_submission(control)
        _save(guest, control_task_key, control)
        st.session_state[keys.submit] = True

    if st.session_state.get(keys.clear, False):
        confirmed = st.checkbox("确认清空当前草稿", key=f"{keys.clear}_confirmed")
        if st.button("执行清空", disabled=not confirmed):
            registry = st.session_state.get("writing_draft_registry")
            if isinstance(registry, dict):
                registry.pop(keys.registry, None)
                st.session_state["writing_draft_registry"] = registry
            for key in vars(keys).values():
                st.session_state.pop(key, None)
            clear_exam_control(
                st.session_state,
                user_id=guest.id,
                skill="writing",
                task_key=control_task_key,
            )
            st.rerun()

    if not st.session_state.get(keys.submit, False):
        return
    st.warning("完成后本次结果只保存在当前会话，不会写入长期学习记录。")
    back, confirm = st.columns(2)
    if back.button("返回编辑", use_container_width=True):
        if control is not None:
            _save(guest, control_task_key, cancel_submission(control))
        st.session_state[keys.submit] = False
        st.rerun()
    if not confirm.button("确认完成", type="primary", use_container_width=True):
        return
    checks = inspect_writing_locally(content, minimum_words=minimum_words)
    st.session_state[result_key] = {
        "word_count": checks.word_count,
        "paragraph_count": checks.paragraph_count,
        "meets_length": checks.meets_recommended_length,
    }
    st.session_state[keys.submit] = False
    if control is not None:
        _save(guest, control_task_key, mark_submitted(control))
    st.rerun()
