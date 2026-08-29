"""Session-only Listening Vocabulary Lab for signed-in users and guests."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from ielts_ai_coach.auth import GuestIdentity
from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.listening_vocabulary import (
    LearningSession,
    SpellingSession,
    advance_learning,
    advance_spelling,
    build_spelling_summary,
    load_vocabulary_bank,
    start_learning,
    start_spelling,
    submit_spelling_answer,
    valid_learning_session,
    valid_spelling_session,
)
from ielts_ai_coach.ui.vocabulary_speech import render_vocabulary_speech


Participant = User | GuestIdentity


def _key(participant_id: int, name: str) -> str:
    """Return one participant-scoped transient-state key."""

    return f"listening_vocab_{name}_{participant_id}"


def _set_mode(participant_id: int, mode: str) -> None:
    """Select one known Vocabulary Lab screen."""

    if mode not in {"home", "study", "review", "spelling", "summary"}:
        raise ValueError("invalid_listening_vocabulary_mode")
    st.session_state[_key(participant_id, "mode")] = mode


def _render_header() -> None:
    """Render the honest product identity shared by every mode."""

    st.title("Listening Vocabulary Lab")
    st.markdown("## 听力词汇训练")
    st.caption("听发音 · 记单词 · 练拼写")


def _start_learning(participant_id: int, *, word_ids: tuple[str, ...] | None = None) -> None:
    """Create a fresh normal or wrong-word learning session."""

    bank = load_vocabulary_bank()
    st.session_state[_key(participant_id, "learning")] = start_learning(
        bank,
        word_ids=word_ids,
    )
    _set_mode(participant_id, "review" if word_ids is not None else "study")


def _start_spelling(participant_id: int, *, prefer_recent: bool) -> None:
    """Create a fresh ten-question spelling round."""

    recent = st.session_state.get(_key(participant_id, "recent"))
    recent_ids = recent if prefer_recent and isinstance(recent, tuple) else None
    st.session_state[_key(participant_id, "spelling")] = start_spelling(
        load_vocabulary_bank(),
        recent_word_ids=recent_ids,
    )
    round_key = _key(participant_id, "round")
    st.session_state[round_key] = int(st.session_state.get(round_key, 0)) + 1
    _set_mode(participant_id, "spelling")


def _render_home(participant_id: int) -> None:
    """Render the two-action Listening Vocabulary Lab landing page."""

    _render_header()
    st.markdown("**IELTS Core Vocabulary · 雅思核心训练词汇**")
    learned = int(st.session_state.get(_key(participant_id, "learned_total"), 0))
    correct = int(st.session_state.get(_key(participant_id, "correct_total"), 0))
    attempts = int(st.session_state.get(_key(participant_id, "attempt_total"), 0))
    metrics = st.columns(2)
    metrics[0].metric("本次已学习", learned)
    metrics[1].metric("本次拼写正确", f"{correct} / {attempts}")
    with st.container(key="listening_vocab_actions"):
        study, spelling = st.columns(2)
        if study.button("开始学习", type="primary", use_container_width=True):
            _start_learning(participant_id)
            st.rerun()
        if spelling.button("拼写挑战", use_container_width=True):
            _start_spelling(participant_id, prefer_recent=True)
            st.rerun()
    st.caption("IELTS 导向的词汇听辨与拼写练习，不是完整 IELTS Listening 模考。")


def _record_learning_completion(
    participant_id: int,
    session: LearningSession,
    *,
    remember_recent: bool,
) -> LearningSession:
    """Count one completed group once and optionally retain it for spelling."""

    if session.completion_recorded:
        return session
    total_key = _key(participant_id, "learned_total")
    st.session_state[total_key] = int(st.session_state.get(total_key, 0)) + len(
        session.word_ids
    )
    if remember_recent:
        st.session_state[_key(participant_id, "recent")] = session.word_ids
    return replace(session, completion_recorded=True)


def _render_learning(participant_id: int, *, review: bool) -> None:
    """Render one simple vocabulary card at a time."""

    _render_header()
    session = st.session_state.get(_key(participant_id, "learning"))
    bank = load_vocabulary_bank()
    if not valid_learning_session(session, bank):
        if review:
            _set_mode(participant_id, "home")
        else:
            _start_learning(participant_id)
        st.rerun()
        return
    assert isinstance(session, LearningSession)
    if session.completed:
        st.success("学习完成")
        st.markdown(f"你刚刚学习了 {len(session.word_ids)} 个单词。")
        with st.container(key="listening_vocab_actions"):
            if review:
                if st.button("返回 Listening", use_container_width=True):
                    _set_mode(participant_id, "home")
                    st.rerun()
            else:
                start, back = st.columns(2)
                if start.button("开始拼写测试", type="primary", use_container_width=True):
                    _start_spelling(participant_id, prefer_recent=True)
                    st.rerun()
                if back.button("返回 Listening", use_container_width=True):
                    _set_mode(participant_id, "home")
                    st.rerun()
        return
    entry = bank.by_id[session.current_word_id]
    st.caption(f"{'错词复习' if review else '学习单词'} · {session.current_index + 1} / {len(session.word_ids)}")
    st.progress((session.current_index + 1) / len(session.word_ids))
    st.markdown(
        '<section class="vocabulary-card">'
        f'<div class="vocabulary-word">{entry.word}</div>'
        f'<div class="vocabulary-part">{entry.part_of_speech} · {entry.level}</div>'
        f'<div class="vocabulary-meaning">{entry.meaning_zh}</div>'
        "</section>",
        unsafe_allow_html=True,
    )
    render_vocabulary_speech(
        entry.word,
        key=f"vocabulary_study_speech_{participant_id}_{entry.entry_id}",
    )
    with st.container(key="listening_vocab_actions"):
        if st.button("下一个", type="primary", use_container_width=True):
            session = advance_learning(session)
            if session.completed:
                session = _record_learning_completion(
                    participant_id,
                    session,
                    remember_recent=not review,
                )
            st.session_state[_key(participant_id, "learning")] = session
            st.rerun()


def _render_spelling_feedback(session: SpellingSession) -> None:
    """Render deterministic locked feedback for the current answer."""

    bank = load_vocabulary_bank()
    attempt = session.attempts[-1]
    entry = bank.by_id[attempt.word_id]
    if attempt.correct:
        st.success("✓ Correct · 正确")
        st.markdown(f"**{entry.word}** · {entry.meaning_zh} · {entry.part_of_speech}")
        st.markdown("**+10 分**")
    else:
        st.error("✗ Incorrect · 错误")
        st.markdown(f"你的答案：`{attempt.answer or '（空）'}`")
        st.markdown(f"正确答案：**{entry.word}**")
        st.markdown(f"{entry.meaning_zh} · {entry.part_of_speech}")


def _render_spelling(participant_id: int) -> None:
    """Render one listen-first spelling question and lock its answer once."""

    _render_header()
    session = st.session_state.get(_key(participant_id, "spelling"))
    bank = load_vocabulary_bank()
    if not valid_spelling_session(session, bank):
        _start_spelling(participant_id, prefer_recent=True)
        st.rerun()
        return
    assert isinstance(session, SpellingSession)
    entry = bank.by_id[session.current_word_id]
    st.caption(f"拼写挑战 · 第 {session.current_index + 1} / {len(session.word_ids)} 题")
    st.progress((session.current_index + 1) / len(session.word_ids))
    round_id = int(st.session_state.get(_key(participant_id, "round"), 0))
    render_vocabulary_speech(
        entry.word,
        key=f"vocabulary_spell_speech_{participant_id}_{round_id}_{session.current_index}",
    )
    if not session.awaiting_advance:
        answer = st.text_input(
            "请输入你听到的单词",
            key=f"vocabulary_answer_{participant_id}_{round_id}_{session.current_index}",
            autocomplete="off",
        )
        with st.container(key="listening_vocab_actions"):
            if st.button("提交", type="primary", use_container_width=True):
                if not answer.strip():
                    st.warning("请先输入你听到的单词。")
                else:
                    session = submit_spelling_answer(session, bank, answer)
                    st.session_state[_key(participant_id, "spelling")] = session
                    attempt_key = _key(participant_id, "attempt_total")
                    correct_key = _key(participant_id, "correct_total")
                    st.session_state[attempt_key] = int(st.session_state.get(attempt_key, 0)) + 1
                    st.session_state[correct_key] = int(st.session_state.get(correct_key, 0)) + int(
                        session.attempts[-1].correct
                    )
                    st.rerun()
        return
    _render_spelling_feedback(session)
    with st.container(key="listening_vocab_actions"):
        if st.button("下一题", type="primary", use_container_width=True):
            session = advance_spelling(session)
            st.session_state[_key(participant_id, "spelling")] = session
            if session.completed:
                _set_mode(participant_id, "summary")
            st.rerun()


def _render_summary(participant_id: int) -> None:
    """Render exact round results, wrong words, replay, and review actions."""

    _render_header()
    session = st.session_state.get(_key(participant_id, "spelling"))
    bank = load_vocabulary_bank()
    if not valid_spelling_session(session, bank) or not session.completed:
        _set_mode(participant_id, "home")
        st.rerun()
        return
    assert isinstance(session, SpellingSession)
    summary = build_spelling_summary(session)
    st.success("拼写挑战完成")
    metrics = st.columns(3)
    metrics[0].metric("正确", f"{summary.correct_count} / {summary.total_questions}")
    metrics[1].metric("正确率", f"{summary.accuracy * 100:.0f}%")
    metrics[2].metric("本局得分", f"{summary.score} / {summary.max_score}")
    st.markdown("### 需要复习")
    if summary.wrong_word_ids:
        st.write(" · ".join(bank.by_id[word_id].word for word_id in summary.wrong_word_ids))
    else:
        st.caption("本局全部正确。")
    with st.container(key="listening_vocab_actions"):
        replay, review, back = st.columns(3)
        if replay.button("再来一局", type="primary", use_container_width=True):
            _start_spelling(participant_id, prefer_recent=False)
            st.rerun()
        if summary.wrong_word_ids and review.button(
            "重新学习这些词", use_container_width=True
        ):
            _start_learning(participant_id, word_ids=summary.wrong_word_ids)
            st.rerun()
        if back.button("返回 Listening", use_container_width=True):
            _set_mode(participant_id, "home")
            st.rerun()


def render_listening_vocabulary_page(participant: Participant) -> None:
    """Render the database-free Listening Vocabulary Lab entry and active flow."""

    mode = st.session_state.get(_key(participant.id, "mode"), "home")
    if mode == "home":
        _render_home(participant.id)
    elif mode in {"study", "review"}:
        _render_learning(participant.id, review=mode == "review")
    elif mode == "spelling":
        _render_spelling(participant.id)
    elif mode == "summary":
        _render_summary(participant.id)
    else:
        _set_mode(participant.id, "home")
        st.rerun()
