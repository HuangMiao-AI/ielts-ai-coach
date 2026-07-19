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


def _question_ids(state: ReadingPracticeState) -> tuple[str, ...]:
    """Return stable question identifiers for one practice."""

    return tuple(question.question_id for question in state.passage.questions)


def _render_instructions(user: User, state: ReadingPracticeState, selected_key: str) -> None:
    """Render rules before starting the stable exam timer."""

    st.title(state.passage.title)
    st.subheader("考试说明")
    st.write(
        f"本练习共 {len(state.passage.questions)} 题，建议在 60 分钟内完成。"
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
        )
        save_exam_session(st.session_state, start_exam(session))
        st.rerun()


def _render_question_strip(state: ReadingPracticeState, session) -> None:
    """Render compact numbered question navigation."""

    st.caption("题目导航")
    for offset in range(0, len(session.question_ids), 5):
        columns = st.columns(5)
        indexes = range(offset, min(offset + 5, len(session.question_ids)))
        for column, index in zip(columns, indexes):
            question_id = session.question_ids[index]
            label = f"{index + 1}{' ✓' if question_id in session.answers else ''}"
            if column.button(
                label,
                key=f"reading_jump_{state.task.id}_{question_id}",
                type="primary" if index == session.current_index else "secondary",
                use_container_width=True,
            ):
                save_exam_session(
                    st.session_state,
                    jump_to_question(session, question_id),
                )
                st.rerun()


def _save_visible_answer(user: User, state: ReadingPracticeState, session):
    """Render and save the current answer without exposing review data."""

    question = state.passage.questions[session.current_index]
    answer = render_reading_exam_question(
        question,
        index=session.current_index + 1,
        total=len(session.question_ids),
        widget_key=(
            f"reading_exam_answer_{user.id}_{state.task.id}_"
            f"{question.question_id}"
        ),
        saved_answer=session.answers.get(question.question_id, ""),
    )
    if answer and session.answers.get(question.question_id) != answer:
        session = answer_question(session, question.question_id, answer)
        save_exam_session(st.session_state, session)
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
    """Render article, one question, timer, navigation, and submit action."""

    minutes, seconds = divmod(remaining_seconds(session), 60)
    st.title(state.passage.title)
    st.caption(
        f"剩余时间 {minutes:02d}:{seconds:02d} · "
        f"已答 {len(session.answers)}/{len(session.question_ids)}"
    )
    mode = st.segmented_control(
        "阅读区域",
        ["双栏", "文章", "题目"],
        default="双栏",
        key=f"reading_layout_{user.id}_{state.task.id}",
    )
    if mode == "文章":
        render_reading_passage(state.passage)
    elif mode == "题目":
        session = _save_visible_answer(user, state, session)
    else:
        article_column, question_column = st.columns([3, 2])
        with article_column:
            render_reading_passage(state.passage)
        with question_column:
            session = _save_visible_answer(user, state, session)
    _render_question_strip(state, session)
    previous, next_column = st.columns(2)
    if previous.button(
        "上一题",
        disabled=session.current_index == 0,
        use_container_width=True,
    ):
        save_exam_session(st.session_state, move_question(session, -1))
        st.rerun()
    if session.current_index < len(session.question_ids) - 1:
        if next_column.button("下一题", use_container_width=True):
            save_exam_session(st.session_state, move_question(session, 1))
            st.rerun()
        return
    if next_column.button("检查并提交", type="primary", use_container_width=True):
        try:
            confirmation = request_submission(session)
        except ReadingExamError:
            missing = len(unanswered_question_ids(session))
            st.error(f"还有 {missing} 题未完成，请先补充答案。")
        else:
            save_exam_session(st.session_state, confirmation)
            _render_confirmation(user, state, confirmation)


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
    )
    if session.phase is ReadingExamPhase.INSTRUCTIONS:
        _render_instructions(user, state, selected_key)
    elif session.phase is ReadingExamPhase.SUBMIT_CONFIRMATION:
        _render_confirmation(user, state, session)
    else:
        _render_workspace(user, state, session)
