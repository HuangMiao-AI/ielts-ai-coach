"""Original offline Listening mini tests with deterministic session scoring."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.listening_bank import (
    ListeningQuestion,
    ListeningTest,
    get_listening_test,
    load_listening_bank,
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
)
from ielts_ai_coach.services.skill_sessions import (
    SkillSession,
    move_item,
    remaining_seconds,
    start_session,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _selected_test_key(user_id: int) -> str:
    """Return the selected-test key for one authenticated user."""

    return f"listening_selected_test_{user_id}"


def _render_library(user: User) -> None:
    """Render both bundled original mini tests."""

    bank = load_listening_bank()
    st.title("听力练习")
    st.caption(bank.copyright_notice)
    st.info("音频、题目和评分均在本地运行；本阶段结果仅保存在当前会话。")
    for index, test in enumerate(bank.tests, start=1):
        with st.container(border=True):
            st.markdown(f"### Test {index} · {test.title}")
            st.caption(
                f"2 Sections · {len(test.questions)} 题 · "
                f"约 {test.estimated_minutes} 分钟 · 本地 WAV 音频"
            )
            result = st.session_state.get(
                listening_result_key(user.id, test.test_id)
            )
            if isinstance(result, ListeningScore):
                st.success(
                    f"本次会话已完成：{result.correct_count}/"
                    f"{result.total_questions}"
                )
            if st.button(
                f"开始 Test {index}",
                key=f"listening_start_{user.id}_{test.test_id}",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[_selected_test_key(user.id)] = test.test_id
                session_key = listening_session_key(user.id, test.test_id)
                saved = st.session_state.get(session_key)
                st.session_state[session_key] = start_session(
                    session=saved if isinstance(saved, SkillSession) else None,
                    user_id=user.id,
                    skill="listening",
                    task_key=test.test_id,
                    item_count=len(test.questions),
                    duration_seconds=test.estimated_minutes * 60,
                )
                st.rerun()


def _save_current_answer(
    user: User,
    test: ListeningTest,
    question: ListeningQuestion,
) -> None:
    """Render and retain one answer without exposing its key."""

    key = listening_answer_key(user.id, test.test_id)
    answers = st.session_state.get(key)
    if not isinstance(answers, dict):
        answers = {}
    saved = str(answers.get(question.question_id, ""))
    widget_key = (
        f"listening_question_{user.id}_{test.test_id}_"
        f"{question.question_id}"
    )
    if question.question_type == "multiple_choice":
        index = question.options.index(saved) if saved in question.options else None
        answer = st.radio(
            question.question,
            question.options,
            index=index,
            key=widget_key,
        )
    else:
        answer = st.text_input(
            question.question,
            value=saved,
            key=widget_key,
            placeholder="请输入听到的答案",
        )
    if isinstance(answer, str) and answer.strip():
        answers[question.question_id] = answer
    else:
        answers.pop(question.question_id, None)
    st.session_state[key] = answers


def _render_question_navigation(
    user: User,
    test: ListeningTest,
    session: SkillSession,
) -> None:
    """Render numbered and sequential question navigation."""

    st.caption("题号导航")
    columns = st.columns(8)
    session_key = listening_session_key(user.id, test.test_id)
    for index in range(len(test.questions)):
        if columns[index % 8].button(
            str(index + 1),
            key=f"listening_jump_{user.id}_{test.test_id}_{index}",
            type="primary" if index == session.current_index else "secondary",
            use_container_width=True,
        ):
            st.session_state[session_key] = move_item(
                session,
                index - session.current_index,
            )
            st.rerun()


def _render_submit_controls(
    user: User,
    test: ListeningTest,
    session: SkillSession,
) -> None:
    """Render previous/next actions and explicit final confirmation."""

    session_key = listening_session_key(user.id, test.test_id)
    answers_key = listening_answer_key(user.id, test.test_id)
    answers = st.session_state.get(answers_key, {})
    answered = len(answers) if isinstance(answers, dict) else 0
    remaining = len(test.questions) - answered
    st.caption(f"已答 {answered}/{len(test.questions)} · 未答 {remaining}")

    previous, next_column = st.columns(2)
    if previous.button(
        "上一题",
        disabled=session.current_index == 0,
        use_container_width=True,
    ):
        st.session_state[session_key] = move_item(session, -1)
        st.rerun()
    if session.current_index < len(test.questions) - 1:
        if next_column.button("下一题", use_container_width=True):
            st.session_state[session_key] = move_item(session, 1)
            st.rerun()
    elif next_column.button(
        "检查并提交",
        type="primary",
        use_container_width=True,
    ):
        if remaining:
            st.session_state[f"{session_key}_incomplete"] = remaining
        else:
            st.session_state[
                listening_confirmation_key(user.id, test.test_id)
            ] = True
        st.rerun()

    incomplete = st.session_state.pop(f"{session_key}_incomplete", None)
    if isinstance(incomplete, int):
        st.error(f"还有 {incomplete} 题未作答，请完成后再提交。")
    confirm_key = listening_confirmation_key(user.id, test.test_id)
    if st.session_state.get(confirm_key) is True:
        st.warning("提交后无法修改答案。请确认提交本次听力练习。")
        confirm, cancel = st.columns(2)
        if confirm.button(
            "确认提交",
            type="primary",
            use_container_width=True,
        ):
            score = score_listening_answers(test, answers)
            st.session_state[
                listening_result_key(user.id, test.test_id)
            ] = score
            st.session_state[confirm_key] = False
            st.rerun()
        if cancel.button("返回检查", use_container_width=True):
            st.session_state[confirm_key] = False
            st.rerun()


def _render_result(user: User, test: ListeningTest, score: ListeningScore) -> None:
    """Render session-only deterministic score and full review."""

    st.title("听力练习结果")
    st.caption("结果仅保存在当前会话，不写入数据库或学习分析。")
    total, accuracy = st.columns(2)
    total.metric("总分", f"{score.correct_count}/{score.total_questions}")
    accuracy.metric("正确率", f"{score.accuracy:.0%}")
    for index, result in enumerate(score.results, start=1):
        marker = "✅" if result.is_correct else "❌"
        with st.container(border=True):
            st.markdown(f"### {marker} 第 {index} 题")
            st.write(result.question)
            st.markdown(f"**你的答案：** {result.user_answer}")
            st.markdown(f"**正确答案：** {result.correct_answer}")
            st.markdown(f"**解析：** {result.explanation}")
            st.markdown(f"**音频证据：** {result.evidence}")
    if st.button("返回听力题库", use_container_width=True):
        st.session_state.pop(_selected_test_key(user.id), None)
        st.rerun()


def _render_test(user: User, test: ListeningTest, session: SkillSession) -> None:
    """Render audio, current question, navigation, and submission."""

    result = st.session_state.get(
        listening_result_key(user.id, test.test_id)
    )
    if isinstance(result, ListeningScore):
        _render_result(user, test, result)
        return
    st.title(test.title)
    st.caption("原创本地音频 · 提交前不显示答案或解析")
    audio_path = PROJECT_ROOT / test.audio_path
    st.audio(audio_path.read_bytes(), format="audio/wav")
    minutes, seconds = divmod(remaining_seconds(session), 60)
    question = test.questions[session.current_index]
    section = next(
        item for item in test.sections if question in item.questions
    )
    st.caption(
        f"{section.title} · 剩余 {minutes:02d}:{seconds:02d} · "
        f"第 {session.current_index + 1}/{len(test.questions)} 题"
    )
    st.progress(session.progress)
    _save_current_answer(user, test, question)
    _render_question_navigation(user, test, session)
    _render_submit_controls(user, test, session)


def render_listening_page(user: User) -> None:
    """Render the independent original Listening practice flow."""

    selected = st.session_state.get(_selected_test_key(user.id))
    if not isinstance(selected, str):
        _render_library(user)
        return
    try:
        test = get_listening_test(selected)
    except KeyError:
        st.session_state.pop(_selected_test_key(user.id), None)
        st.rerun()
        return
    session = st.session_state.get(listening_session_key(user.id, test.test_id))
    if not isinstance(session, SkillSession) or session.user_id != user.id:
        st.session_state.pop(_selected_test_key(user.id), None)
        st.rerun()
        return
    _render_test(user, test, session)
