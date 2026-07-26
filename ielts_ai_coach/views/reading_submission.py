"""Reading submission flow coordinated by the shared exam controller."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    cancel_submission as cancel_control_submission,
    mark_submitted as mark_control_submitted,
    request_submission as request_control_submission,
    save_exam_control,
)
from ielts_ai_coach.services.exam_state import (
    ReadingExamError,
    ReadingExamPhase,
    ReadingExamSession,
    cancel_submission,
    mark_submitted,
    pause_exam_session,
    request_submission,
    resume_exam_session,
    timeout_exam_session,
    unanswered_question_ids,
)
from ielts_ai_coach.services.reading_exam import save_exam_session
from ielts_ai_coach.services.reading_practice import (
    ReadingPracticeError,
    ReadingPracticeState,
    submit_reading_practice,
)


def request_reading_submission(
    session: ReadingExamSession,
    control: ExamSession,
) -> tuple[ReadingExamSession, ExamSession]:
    """Open confirmation when complete or after the shared timeout."""

    missing = len(unanswered_question_ids(session))
    st.caption(f"提交前检查：还有 {missing} 题未完成。")
    can_submit = control.status in {
        ExamStatus.RUNNING,
        ExamStatus.TIMED_OUT,
    }
    if not st.button(
        "检查并提交",
        type="primary",
        disabled=not can_submit,
        use_container_width=True,
    ):
        return session, control
    try:
        session = request_submission(
            session,
            allow_incomplete=control.timed_out,
        )
        control = request_control_submission(control)
    except ReadingExamError:
        st.error(f"还有 {missing} 题未完成，请先补充答案。")
    return session, control


def render_reading_confirmation(
    user: User,
    state: ReadingPracticeState,
    session: ReadingExamSession,
    control: ExamSession,
) -> None:
    """Persist one explicitly confirmed Reading attempt."""

    st.subheader("确认提交")
    warning = "提交后无法修改答案，系统将立即进行确定性评分。"
    if control.timed_out:
        warning += " 未作答题目将计为错误。"
    st.warning(warning)
    st.write(f"已完成 {len(session.answers)}/{len(session.question_ids)} 题。")
    back, confirm = st.columns(2)
    if back.button("返回检查", use_container_width=True):
        session = cancel_submission(session)
        control = cancel_control_submission(control)
        if control.status is ExamStatus.TIMED_OUT:
            session = timeout_exam_session(session)
        save_exam_session(st.session_state, session)
        save_exam_control(
            st.session_state,
            user_id=user.id,
            task_key=str(state.task.id),
            session=control,
        )
        st.rerun()
    if not confirm.button(
        "确认提交",
        type="primary",
        use_container_width=True,
    ):
        return
    try:
        submit_reading_practice(
            user_id=user.id,
            task_id=state.task.id,
            answers=session.answers,
            allow_incomplete=control.timed_out,
        )
    except ReadingPracticeError as error:
        if str(error) != "already_submitted":
            st.error("答案提交失败，请刷新后重试。")
            return
    save_exam_session(st.session_state, mark_submitted(session))
    save_exam_control(
        st.session_state,
        user_id=user.id,
        task_key=str(state.task.id),
        session=mark_control_submitted(control),
    )
    st.rerun()


def sync_reading_session(
    session: ReadingExamSession,
    control: ExamSession,
) -> ReadingExamSession:
    """Mirror edit-lock phases from the shared controller."""

    if (
        control.status is ExamStatus.PAUSED
        and session.phase is ReadingExamPhase.IN_PROGRESS
    ):
        return pause_exam_session(session)
    if (
        control.status is ExamStatus.RUNNING
        and session.phase is ReadingExamPhase.PAUSED
    ):
        return resume_exam_session(session)
    if control.status is ExamStatus.TIMED_OUT:
        if session.phase is ReadingExamPhase.SUBMIT_CONFIRMATION:
            session = cancel_submission(session)
        if session.phase is ReadingExamPhase.IN_PROGRESS:
            return timeout_exam_session(session)
    return session
