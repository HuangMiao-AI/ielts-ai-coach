"""Single-component, session-only IELTS Training Arena page."""

from __future__ import annotations

import streamlit as st

from ielts_ai_coach.database.models import User
from ielts_ai_coach.services.training_arena import (
    ArenaRound,
    advance_arena_round,
    answer_arena_question,
    arena_round_key,
    build_arena_summary,
    load_training_arena_bank,
    record_completed_round_score,
    start_arena_round,
)


def _new_round(user: User) -> ArenaRound:
    """Replace only the transient arena round."""

    round_state = start_arena_round(load_training_arena_bank())
    st.session_state[arena_round_key(user.id)] = round_state
    return round_state


def _render_summary(
    user: User,
    round_state: ArenaRound,
    page_refs: dict[str, st.Page],
) -> None:
    """Render the compact end-of-round report."""

    round_state = record_completed_round_score(
        st.session_state,
        user.id,
        round_state,
    )
    st.session_state[arena_round_key(user.id)] = round_state
    summary = build_arena_summary(round_state, load_training_arena_bank())
    st.subheader("本局战绩")
    columns = st.columns(3)
    columns[0].metric("答对题数", f"{summary.correct_count}/{summary.total_questions}")
    columns[1].metric("正确率", f"{summary.accuracy:.0%}")
    columns[2].metric("得分", f"{summary.score}/{summary.max_score}")
    st.markdown("**本局重点词汇**")
    for item in summary.focus_vocabulary:
        st.write(f"- {item}")
    replay, home = st.columns(2)
    if replay.button("再来一局", type="primary", use_container_width=True):
        _new_round(user)
        st.rerun()
    with home:
        st.page_link(page_refs["home"], label="返回首页", use_container_width=True)


def _render_question(user: User, round_state: ArenaRound) -> None:
    """Render either supported question type through one answer component."""

    bank = load_training_arena_bank()
    question = bank.by_id[round_state.question_ids[round_state.current_index]]
    st.caption(
        f"第 {round_state.current_index + 1}/5 题 · "
        f"得分 {round_state.score} · 连击 {round_state.combo}"
    )
    st.progress((round_state.current_index + int(round_state.awaiting_advance)) / 5)
    label = "同义替换" if question.question_type == "synonym" else "词形变化"
    st.markdown(f"### {label}")
    st.caption(question.instruction)
    st.markdown(f"## {question.prompt}")
    with st.container(key="arena_answer_grid"):
        rows = (st.columns(2), st.columns(2))
        for index, option in enumerate(question.options):
            with rows[index // 2][index % 2]:
                if st.button(
                    option,
                    key=f"arena_answer_{round_state.current_index}_{index}",
                    disabled=round_state.awaiting_advance,
                    use_container_width=True,
                ):
                    st.session_state[arena_round_key(user.id)] = answer_arena_question(
                        round_state, question, option
                    )
                    st.rerun()
    if not round_state.awaiting_advance:
        return
    selected = round_state.answers[-1]
    if selected == question.correct_answer:
        st.success("回答正确！+10 分")
    else:
        st.error(f"回答错误。正确答案：{question.correct_answer}")
    st.info(f"{question.explanation_zh}\n\n{question.explanation_en}")
    label = "查看本局战绩" if round_state.current_index == 4 else "下一题"
    if st.button(label, type="primary", use_container_width=True):
        st.session_state[arena_round_key(user.id)] = advance_arena_round(round_state)
        st.rerun()


def render_training_arena_page(user: User, page_refs: dict[str, st.Page]) -> None:
    """Start immediately and keep all game state inside the browser session."""

    st.title("IELTS 训练场")
    st.caption("IELTS Training Arena · 5题一局，快速练习雅思核心能力。")
    round_state = st.session_state.get(arena_round_key(user.id))
    if not isinstance(round_state, ArenaRound):
        round_state = _new_round(user)
    if round_state.completed:
        _render_summary(user, round_state, page_refs)
    else:
        _render_question(user, round_state)
