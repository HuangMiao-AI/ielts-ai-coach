"""Interactive Reading exam workspace and persisted result review."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    load_exam_control,
    save_exam_control,
)
from ielts_ai_coach.services.exam_state import (
    ReadingExamPhase,
    answer_question,
    jump_to_question,
    start_exam,
    unanswered_question_ids,
)
from ielts_ai_coach.services.reading_exam import (
    load_exam_session,
    save_exam_session,
)
from ielts_ai_coach.services.reading_practice import (
    ReadingPracticeState,
)
from ielts_ai_coach.views.task_cards import (
    render_reading_exam_question,
    render_reading_passage,
)
from ielts_ai_coach.views.reading_workspace_resizer import (
    render_workspace_resizer,
)
from ielts_ai_coach.views.reading_workspace_client import (
    reading_workspace_client_key,
    render_reading_navigation_client,
)
from ielts_ai_coach.views.exam_control_panel import (
    ExamControlAction,
    render_exam_control_panel,
)
from ielts_ai_coach.views.reading_submission import (
    render_reading_confirmation,
    request_reading_submission,
    sync_reading_session,
)
from ielts_ai_coach.views.reading_result_view import (
    render_reading_session_result,
)


QUESTION_TYPE_LABELS = {
    "multiple_choice": "Multiple Choice",
    "true_false_not_given": "True / False / Not Given",
    "matching_heading": "Matching Heading",
}


def _question_ids(state: ReadingPracticeState) -> tuple[str, ...]:
    """Return stable question identifiers for one practice."""

    return tuple(question.question_id for question in state.passage.questions)


def _render_instructions(user: User, state: ReadingPracticeState, selected_key: str) -> None:
    """Render rules before starting the stable exam timer."""

    st.title(state.passage.title)
    st.subheader("考试说明")
    st.write(
        f"本练习共 {len(state.passage.questions)} 题，推荐时间：{state.passage.recommended_minutes} 分钟。"
    )
    st.write("提交前不会显示正确答案或解析；确认提交后答案将无法修改。")
    st.caption("草稿只保存在当前浏览器会话中，关闭会话后可能无法恢复。")
    back, start = st.columns(2)
    if back.button("返回题库", use_container_width=True):
        st.session_state.pop(selected_key, None)
        st.rerun()
    if start.button("开始计时练习", type="primary", use_container_width=True):
        session = load_exam_session(
            st.session_state,
            user_id=user.id,
            task_id=state.task.id,
            question_ids=_question_ids(state),
            duration_seconds=state.passage.recommended_minutes * 60,
        )
        session = start_exam(session)
        save_exam_session(st.session_state, session)
        load_exam_control(
            st.session_state,
            user_id=user.id,
            skill="reading",
            task_key=str(state.task.id),
            duration_seconds=session.duration_seconds,
            now=session.started_at,
        )
        st.rerun()


def _render_question_navigation(state: ReadingPracticeState, session) -> None:
    """Render in-page links with answered, current, and pending states."""

    links: list[str] = []
    for index, question_id in enumerate(session.question_ids, start=1):
        status = "answered" if question_id in session.answers else "unanswered"
        current = " current" if index - 1 == session.current_index else ""
        links.append(
            f'<a class="reading-question-link {status}{current}" '
            f'href="#reading-question-{question_id}" '
            f'data-reading-question-id="{question_id}" '
            f'aria-current="{"true" if current else "false"}">{index}</a>'
        )
    st.markdown(
        '<nav class="reading-question-navigation" '
        f'data-reading-question-navigation="{reading_workspace_client_key(user_id=session.user_id, task_id=session.task_id)}" '
        'aria-label="题目导航">' + "".join(links) + "</nav>",
        unsafe_allow_html=True,
    )


def _save_all_answers(
    user: User,
    state: ReadingPracticeState,
    session,
    *,
    editable: bool,
):
    """Render grouped editable questions and retain every scoped draft answer."""

    current_type = ""
    for index, question in enumerate(state.passage.questions, start=1):
        if question.question_type != current_type:
            current_type = question.question_type
            st.markdown(
                f"### {QUESTION_TYPE_LABELS.get(current_type, current_type)}"
            )
        st.markdown(
            f'<div id="reading-question-{question.question_id}" '
            f'class="reading-question-anchor" data-reading-question-id="{question.question_id}"></div>',
            unsafe_allow_html=True,
        )
        answer = render_reading_exam_question(
            question,
            index=index,
            total=len(session.question_ids),
            widget_key=(
                f"reading_exam_answer_{user.id}_{state.task.id}_"
                f"{question.question_id}"
            ),
            saved_answer=session.answers.get(question.question_id, ""),
            disabled=not editable,
        )
        if (
            editable
            and answer
            and session.answers.get(question.question_id) != answer
        ):
            session = answer_question(session, question.question_id, answer)
            session = jump_to_question(session, question.question_id)
    return session


def _render_workspace(
    user: User,
    state: ReadingPracticeState,
    session,
    control: ExamSession,
) -> None:
    """Render an all-question article and answer workspace without answers."""

    st.title(state.passage.title)
    st.caption(
        f"已答 {len(session.answers)}/{len(session.question_ids)} · "
        f"未答 {len(unanswered_question_ids(session))}"
    )
    editable = control.status is ExamStatus.RUNNING
    mode = st.segmented_control(
        "阅读区域",
        ["双栏", "文章", "题目"],
        default="双栏",
        key=f"reading_layout_{user.id}_{state.task.id}",
    )
    if mode == "双栏":
        render_workspace_resizer(user_id=user.id, task_id=state.task.id)
    with st.container(key=f"reading_workspace_{user.id}_{state.task.id}"):
        st.markdown('<div class="reading-workspace"></div>', unsafe_allow_html=True)
        if mode == "双栏":
            article_column, question_column = st.columns([11, 9], gap="small")
            with article_column:
                st.markdown("#### 文章 · 原创练习材料")
                with st.container(height=620, border=True):
                    render_reading_passage(state.passage)
            with question_column:
                st.markdown("#### 题目 · 全部 {0} 题".format(len(session.question_ids)))
                _render_question_navigation(state, session)
                with st.container(height=620, border=True):
                    session = _save_all_answers(
                        user,
                        state,
                        session,
                        editable=editable,
                    )
                    session, control = request_reading_submission(
                        session,
                        control,
                    )
        elif mode == "文章":
            st.markdown("#### 文章 · 原创练习材料")
            with st.container(height=620, border=True):
                render_reading_passage(state.passage)
        else:
            st.markdown("#### 题目 · 全部 {0} 题".format(len(session.question_ids)))
            _render_question_navigation(state, session)
            with st.container(height=620, border=True):
                session = _save_all_answers(
                    user,
                    state,
                    session,
                    editable=editable,
                )
                session, control = request_reading_submission(
                    session,
                    control,
                )
    if mode != "文章":
        render_reading_navigation_client(user_id=user.id, task_id=state.task.id)
    save_exam_session(st.session_state, session)
    save_exam_control(
        st.session_state,
        user_id=user.id,
        task_key=str(state.task.id),
        session=control,
    )
    if session.phase is ReadingExamPhase.SUBMIT_CONFIRMATION:
        render_reading_confirmation(user, state, session, control)


def render_reading_session(
    user: User,
    state: ReadingPracticeState,
    *,
    selected_key: str,
) -> None:
    """Render the correct stage for one selected Reading practice."""

    if state.score is not None:
        render_reading_session_result(user, state, selected_key)
        return
    session = load_exam_session(
        st.session_state,
        user_id=user.id,
        task_id=state.task.id,
        question_ids=_question_ids(state),
        duration_seconds=state.passage.recommended_minutes * 60,
    )
    if session.phase is ReadingExamPhase.INSTRUCTIONS:
        _render_instructions(user, state, selected_key)
        return
    control = load_exam_control(
        st.session_state,
        user_id=user.id,
        skill="reading",
        task_key=str(state.task.id),
        duration_seconds=session.duration_seconds,
        now=session.started_at,
    )
    control, action = render_exam_control_panel(control)
    session = sync_reading_session(session, control)
    save_exam_session(st.session_state, session)
    save_exam_control(
        st.session_state,
        user_id=user.id,
        task_key=str(state.task.id),
        session=control,
    )
    if action in {
        ExamControlAction.PAUSED,
        ExamControlAction.RESUMED,
    }:
        st.rerun()
    if session.phase is ReadingExamPhase.SUBMIT_CONFIRMATION:
        render_reading_confirmation(user, state, session, control)
    else:
        _render_workspace(user, state, session, control)
