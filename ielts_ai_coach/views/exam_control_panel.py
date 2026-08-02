"""Shared Streamlit controls for timed IELTS practice sessions."""

from __future__ import annotations

import hashlib
from enum import Enum

import streamlit as st

from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    pause_exam,
    reconcile_exam,
)
from ielts_ai_coach.ui.exam_timer import ExamTimerEvent, render_exam_timer


class ExamControlAction(str, Enum):
    """UI actions that a skill page may need to mirror locally."""

    NONE = "none"
    PAUSED = "paused"
    RESUMED = "resumed"
    TIMED_OUT = "timed_out"


def _client_key(session: ExamSession) -> str:
    """Return an opaque browser marker for one controller."""

    return hashlib.sha256(session.session_id.encode("utf-8")).hexdigest()[:16]


def _render_live_timer(
    session: ExamSession,
) -> ExamTimerEvent:
    """Keep the visible countdown current without forcing server reruns."""

    client_key = _client_key(session)
    remaining = session.remaining_seconds()
    minutes, seconds = divmod(remaining, 60)
    st.markdown(
        f'<div class="exam-control-status" data-exam-control="{client_key}">'
        f'<strong data-exam-timer>{minutes:02d}:{seconds:02d}</strong>'
        f'<span data-exam-status>{_status_label(session.status)}</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    return render_exam_timer(session, client_key=client_key)


def _status_label(status: ExamStatus) -> str:
    """Translate one controller state for the student UI."""

    return {
        ExamStatus.NOT_STARTED: "未开始",
        ExamStatus.RUNNING: "计时中",
        ExamStatus.PAUSED: "已暂停",
        ExamStatus.SUBMIT_CONFIRM: "等待确认",
        ExamStatus.TIMED_OUT: "时间已到",
        ExamStatus.SUBMITTED: "已提交",
    }[status]


def render_exam_control_panel(
    session: ExamSession,
    *,
    pause_root_key: str | None = None,
) -> tuple[ExamSession, ExamControlAction]:
    """Render a live timer and the transitions shared by all skill pages."""

    reconciled = reconcile_exam(session)
    action = (
        ExamControlAction.TIMED_OUT
        if reconciled.status is ExamStatus.TIMED_OUT
        and session.status is not ExamStatus.TIMED_OUT
        else ExamControlAction.NONE
    )
    session = reconciled
    timer_slot = st.empty()
    if session.status is ExamStatus.RUNNING:
        if st.button(
            "暂停计时",
            key=f"exam_pause_{_client_key(session)}",
            use_container_width=True,
        ):
            session = pause_exam(session)
            action = ExamControlAction.PAUSED

    with timer_slot.container():
        timer_event = _render_live_timer(session)
    if timer_event is ExamTimerEvent.TIMEOUT:
        updated = reconcile_exam(session)
        if (
            updated.status is ExamStatus.TIMED_OUT
            and session.status is not ExamStatus.TIMED_OUT
        ):
            session = updated
            action = ExamControlAction.TIMED_OUT
    if session.status is ExamStatus.PAUSED:
        return session, action
    if session.status is ExamStatus.TIMED_OUT:
        st.warning("时间已到，答案已锁定。未作答题目将在交卷后计为错误。")
    return session, action
