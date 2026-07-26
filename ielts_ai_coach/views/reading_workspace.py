"""Interactive Reading exam workspace and persisted result review."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_state import (
    ReadingExamError,
    ReadingExamPhase,
    answer_question,
    cancel_submission,
    jump_to_question,
    mark_submitted,
    move_question,
    remaining_seconds,
    request_submission,
    start_exam,
    unanswered_question_ids,
)
from ielts_ai_coach.services.reading_exam import (
    clear_exam_session,
    load_exam_session,
    save_exam_session,
)
from ielts_ai_coach.services.reading_practice import (
    ReadingPracticeError,
    ReadingPracticeState,
    submit_reading_practice,
)
from ielts_ai_coach.views.task_cards import (
    render_reading_exam_question,
    render_reading_passage,
    render_reading_result,
    render_reading_result_summary,
)
from ielts_ai_coach.views.reading_workspace_resizer import (
    render_workspace_resizer,
)
from ielts_ai_coach.views.reading_workspace_client import (
    reading_workspace_client_key,
    render_reading_navigation_client,
    render_reading_workspace_client,
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
        save_exam_session(st.session_state, start_exam(session))
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


def _save_all_answers(user: User, state: ReadingPracticeState, session):
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
        )
        if answer and session.answers.get(question.question_id) != answer:
            session = answer_question(session, question.question_id, answer)
            session = jump_to_question(session, question.question_id)
    return session


def _request_submission(session):
    """Open confirmation only when the complete workspace is answered."""

    missing = len(unanswered_question_ids(session))
    st.caption(f"提交前检查：还有 {missing} 题未完成。")
    if not st.button("检查并提交", type="primary", use_container_width=True):
        return session
    try:
        return request_submission(session)
    except ReadingExamError:
        st.error(f"还有 {missing} 题未完成，请先补充答案。")
        return session


def _render_confirmation(user: User, state: ReadingPracticeState, session) -> None:
    """Require an explicit irreversible submission confirmation."""

    st.subheader("确认提交")
    st.warning("提交后无法修改答案，系统将立即进行确定性评分。")
    st.write(f"已完成 {len(session.answers)}/{len(session.question_ids)} 题。")
    back, confirm = st.columns(2)
    if back.button("返回检查", use_container_width=True):
        save_exam_session(st.session_state, cancel_submission(session))
        st.rerun()
    if not confirm.button("确认提交", type="primary", use_container_width=True):
        return
    try:
        submit_reading_practice(
            user_id=user.id,
            task_id=state.task.id,
            answers=session.answers,
        )
    except ReadingPracticeError as error:
        if str(error) != "already_submitted":
            st.error("答案提交失败，请刷新后重试。")
            return
    save_exam_session(st.session_state, mark_submitted(session))
    st.rerun()


def _render_workspace(user: User, state: ReadingPracticeState, session) -> None:
    """Render an all-question article and answer workspace without answers."""

    minutes, seconds = divmod(remaining_seconds(session), 60)
    assert session.started_at is not None
    client_key = reading_workspace_client_key(
        user_id=user.id,
        task_id=state.task.id,
    )
    st.title(state.passage.title)
    st.markdown(
        f'<div class="reading-workspace-status" data-reading-timer="{client_key}">'
        "剩余时间 <span data-reading-timer-display>"
        f"{minutes:02d}:{seconds:02d}</span> · "
        f"已答 {len(session.answers)}/{len(session.question_ids)} · "
        f"未答 {len(unanswered_question_ids(session))}"
        " <span class=\"reading-timer-notice\" data-reading-timer-notice></span>"
        "</div>",
        unsafe_allow_html=True,
    )
    render_reading_workspace_client(
        user_id=user.id,
        task_id=state.task.id,
        started_at=session.started_at,
        duration_seconds=session.duration_seconds,
    )
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
                    session = _save_all_answers(user, state, session)
                    session = _request_submission(session)
        elif mode == "文章":
            st.markdown("#### 文章 · 原创练习材料")
            with st.container(height=620, border=True):
                render_reading_passage(state.passage)
        else:
            st.markdown("#### 题目 · 全部 {0} 题".format(len(session.question_ids)))
            _render_question_navigation(state, session)
            with st.container(height=620, border=True):
                session = _save_all_answers(user, state, session)
                session = _request_submission(session)
    if mode != "文章":
        render_reading_navigation_client(user_id=user.id, task_id=state.task.id)
    save_exam_session(st.session_state, session)
    if session.phase is ReadingExamPhase.SUBMIT_CONFIRMATION:
        _render_confirmation(user, state, session)


def _render_result(
    user: User,
    state: ReadingPracticeState,
    selected_key: str,
) -> None:
    """Render persisted result summary and opt-in complete review."""

    assert state.score is not None
    st.title("阅读练习结果")
    st.success("评分、任务完成状态和学习日志已同步保存。")
    render_reading_result_summary(state.score)
    review_key = f"reading_review_open_{user.id}_{state.task.id}"
    if not st.session_state.get(review_key, False):
        if st.button("查看逐题解析", type="primary", use_container_width=True):
            st.session_state[review_key] = True
            st.rerun()
    else:
        render_reading_result(state.score)
    if st.button("返回题库", key="reading_result_back"):
        st.session_state.pop(selected_key, None)
        clear_exam_session(
            st.session_state,
            user_id=user.id,
            task_id=state.task.id,
        )
        st.rerun()


def render_reading_session(
    user: User,
    state: ReadingPracticeState,
    *,
    selected_key: str,
) -> None:
    """Render the correct stage for one selected Reading practice."""

    if state.score is not None:
        _render_result(user, state, selected_key)
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
    elif session.phase is ReadingExamPhase.SUBMIT_CONFIRMATION:
        _render_confirmation(user, state, session)
    else:
        _render_workspace(user, state, session)
