"""Original offline Listening practice with controller-owned audio and timing."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.exam_controls import (
    ExamSession,
    ExamStatus,
    cancel_submission as cancel_control_submission,
    load_exam_control,
    mark_submitted as mark_control_submitted,
    request_submission as request_control_submission,
    resume_exam,
    save_exam_control,
)
from ielts_ai_coach.services.listening_bank import (
    ListeningQuestion,
    ListeningTest,
    get_listening_test,
)
from ielts_ai_coach.services.listening_scoring import (
    ListeningScore,
    score_listening_answers,
)
from ielts_ai_coach.services.listening_session import (
    listening_answer_key,
    listening_confirmation_key,
    listening_result_key,
    listening_session_key,
    request_listening_audio_command,
    selected_test_key,
)
from ielts_ai_coach.services.skill_sessions import SkillSession, move_item
from ielts_ai_coach.views.exam_control_panel import (
    ExamControlAction,
    render_exam_control_panel,
)
from ielts_ai_coach.views.exam_hard_pause import (
    render_hard_pause_overlay,
)
from ielts_ai_coach.views.listening_audio import (
    render_controlled_listening_audio,
    render_listening_toolbar,
)
from ielts_ai_coach.views.listening_start import render_listening_formal_start
from ielts_ai_coach.views.listening_sections import (
    render_listening_library,
    render_listening_result,
)


def _save_current_answer(
    user: User,
    test: ListeningTest,
    question: ListeningQuestion,
    *,
    editable: bool,
) -> None:
    """Render and retain one answer without exposing its answer key."""

    key = listening_answer_key(user.id, test.test_id)
    answers = st.session_state.get(key)
    if not isinstance(answers, dict):
        answers = {}
    saved = str(answers.get(question.question_id, ""))
    widget_key = f"listening_question_{user.id}_{test.test_id}_{question.question_id}"
    if question.question_type == "multiple_choice":
        index = question.options.index(saved) if saved in question.options else None
        answer = st.radio(
            question.question,
            question.options,
            index=index,
            key=widget_key,
            disabled=not editable,
        )
    else:
        answer = st.text_input(
            question.question,
            value=saved,
            key=widget_key,
            placeholder="请输入听到的答案",
            disabled=not editable,
        )
    if editable:
        if isinstance(answer, str) and answer.strip():
            answers[question.question_id] = answer
        else:
            answers.pop(question.question_id, None)
    st.session_state[key] = answers


def _render_question_navigation(user: User, test: ListeningTest, session: SkillSession) -> None:
    """Render numbered question navigation without persistent bright highlighting."""

    st.caption("题号导航")
    columns = st.columns(8)
    session_key = listening_session_key(user.id, test.test_id)
    for index in range(len(test.questions)):
        if columns[index % 8].button(
            str(index + 1),
            key=f"listening_jump_{user.id}_{test.test_id}_{index}",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[session_key] = move_item(session, index - session.current_index)
            st.rerun()


def _render_submit_controls(
    user: User,
    test: ListeningTest,
    session: SkillSession,
    control: ExamSession,
) -> None:
    """Render navigation and explicit final confirmation without duplicate scoring."""

    session_key = listening_session_key(user.id, test.test_id)
    answers_key = listening_answer_key(user.id, test.test_id)
    answers = st.session_state.get(answers_key, {})
    answered = len(answers) if isinstance(answers, dict) else 0
    remaining = len(test.questions) - answered
    st.caption(f"已答 {answered}/{len(test.questions)} · 未答 {remaining}")
    previous, next_column = st.columns(2)
    if previous.button("上一题", disabled=session.current_index == 0, use_container_width=True):
        st.session_state[session_key] = move_item(session, -1)
        st.rerun()
    if session.current_index < len(test.questions) - 1:
        if next_column.button("下一题", use_container_width=True):
            st.session_state[session_key] = move_item(session, 1)
            st.rerun()
    elif next_column.button(
        "检查并提交",
        type="primary",
        disabled=control.status not in {ExamStatus.RUNNING, ExamStatus.TIMED_OUT},
        use_container_width=True,
    ):
        if remaining and not control.timed_out:
            st.session_state[f"{session_key}_incomplete"] = remaining
        else:
            control = request_control_submission(control)
            request_listening_audio_command(st.session_state, user.id, test.test_id, "stop")
            save_exam_control(st.session_state, user_id=user.id, task_key=test.test_id, session=control)
            st.session_state[listening_confirmation_key(user.id, test.test_id)] = True
        st.rerun()
    incomplete = st.session_state.pop(f"{session_key}_incomplete", None)
    if isinstance(incomplete, int):
        st.error(f"还有 {incomplete} 题未作答，请完成后再提交。")
    confirm_key = listening_confirmation_key(user.id, test.test_id)
    if st.session_state.get(confirm_key) is not True:
        return
    if control.status is ExamStatus.TIMED_OUT:
        control = request_control_submission(control)
        save_exam_control(st.session_state, user_id=user.id, task_key=test.test_id, session=control)
    warning = "提交后无法修改答案。请确认提交本次听力练习。"
    if control.timed_out:
        warning += " 未作答题目将在交卷后计为错误。"
    st.warning(warning)
    confirm, cancel = st.columns(2)
    if confirm.button("确认提交", type="primary", use_container_width=True):
        score = score_listening_answers(test, answers, allow_incomplete=control.timed_out)
        st.session_state[listening_result_key(user.id, test.test_id)] = score
        save_exam_control(
            st.session_state,
            user_id=user.id,
            task_key=test.test_id,
            session=mark_control_submitted(control),
        )
        st.session_state[confirm_key] = False
        st.rerun()
    if cancel.button("返回检查", use_container_width=True):
        save_exam_control(
            st.session_state,
            user_id=user.id,
            task_key=test.test_id,
            session=cancel_control_submission(control),
        )
        st.session_state[confirm_key] = False
        st.rerun()


def _render_test(user: User, test: ListeningTest, session: SkillSession) -> None:
    """Render one official session, audio state, questions, and submission flow."""

    result = st.session_state.get(listening_result_key(user.id, test.test_id))
    if isinstance(result, ListeningScore):
        render_listening_result(user, test, result)
        return
    control = load_exam_control(
        st.session_state,
        user_id=user.id,
        skill="listening",
        task_key=test.test_id,
        duration_seconds=session.duration_seconds,
        now=session.started_at,
    )
    root_key = f"exam_root_listening_{user.id}_{test.test_id}"
    control, action = render_exam_control_panel(
        control,
        pause_root_key=root_key,
    )
    if action is ExamControlAction.PAUSED:
        request_listening_audio_command(st.session_state, user.id, test.test_id, "pause")
    elif action is ExamControlAction.TIMED_OUT:
        request_listening_audio_command(st.session_state, user.id, test.test_id, "stop")
    save_exam_control(st.session_state, user_id=user.id, task_key=test.test_id, session=control)
    st.title(test.title)
    st.caption("原创本地音频 · 仅在正式开始后计时 · 提交前不显示答案或解析")
    audio_state = render_controlled_listening_audio(user, test, control)
    if control.status is ExamStatus.PAUSED:
        if render_hard_pause_overlay(control, subject="听力", root_key=root_key):
            control = resume_exam(control)
            request_listening_audio_command(st.session_state, user.id, test.test_id, "resume")
            save_exam_control(st.session_state, user_id=user.id, task_key=test.test_id, session=control)
            st.rerun()
        return
    question = test.questions[session.current_index]
    section = next(item for item in test.sections if question in item.questions)
    answers = st.session_state.get(listening_answer_key(user.id, test.test_id), {})
    render_listening_toolbar(
        test,
        question_number=session.current_index + 1,
        section_title=section.title,
        answered=len(answers) if isinstance(answers, dict) else 0,
        state=audio_state,
    )
    st.progress(session.progress)
    _save_current_answer(user, test, question, editable=control.status is ExamStatus.RUNNING)
    _render_question_navigation(user, test, session)
    _render_submit_controls(user, test, session, control)


def render_listening_page(user: User) -> None:
    """Render the independent original Listening formal-start and exam flow."""

    selected = st.session_state.get(selected_test_key(user.id))
    if not isinstance(selected, str):
        render_listening_library(user)
        return
    try:
        test = get_listening_test(selected)
    except KeyError:
        st.session_state.pop(selected_test_key(user.id), None)
        st.rerun()
        return
    session = st.session_state.get(listening_session_key(user.id, test.test_id))
    if not isinstance(session, SkillSession) or session.user_id != user.id:
        render_listening_formal_start(user, test)
        return
    _render_test(user, test, session)
