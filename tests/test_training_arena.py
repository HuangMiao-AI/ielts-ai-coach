"""Pure contracts for the session-only IELTS Training Arena."""

from __future__ import annotations

import random

import pytest

from ielts_ai_coach.services.training_arena import (
    advance_arena_round,
    answer_arena_question,
    arena_round_key,
    build_arena_summary,
    load_training_arena_bank,
    start_arena_round,
)


def test_bank_has_twenty_unique_questions_per_supported_type() -> None:
    bank = load_training_arena_bank()
    counts = {kind: 0 for kind in ("synonym", "word_form")}
    for question in bank.questions:
        counts[question.question_type] += 1
        assert len(question.options) == len(set(question.options)) == 4
        assert question.correct_answer in question.options
        assert question.explanation_en
        assert question.explanation_zh
        assert question.focus_vocabulary
    assert counts == {"synonym": 20, "word_form": 20}
    assert len({question.question_id for question in bank.questions}) == 40


def test_round_has_five_unique_questions_and_both_types() -> None:
    bank = load_training_arena_bank()
    round_state = start_arena_round(bank, rng=random.Random(7))
    questions = [bank.by_id[question_id] for question_id in round_state.question_ids]
    assert len(set(round_state.question_ids)) == 5
    assert {question.question_type for question in questions} == {
        "synonym",
        "word_form",
    }


def test_scoring_feedback_combo_and_summary_are_deterministic() -> None:
    bank = load_training_arena_bank()
    round_state = start_arena_round(bank, rng=random.Random(3))
    first = bank.by_id[round_state.question_ids[0]]
    round_state = answer_arena_question(round_state, first, first.correct_answer)
    assert round_state.score == 10
    assert round_state.combo == 1
    assert round_state.awaiting_advance is True
    with pytest.raises(ValueError, match="question_already_answered"):
        answer_arena_question(round_state, first, first.correct_answer)

    round_state = advance_arena_round(round_state)
    second = bank.by_id[round_state.question_ids[1]]
    wrong = next(option for option in second.options if option != second.correct_answer)
    round_state = answer_arena_question(round_state, second, wrong)
    assert round_state.score == 10
    assert round_state.combo == 0

    while not round_state.completed:
        round_state = advance_arena_round(round_state)
        if round_state.completed:
            break
        question = bank.by_id[round_state.question_ids[round_state.current_index]]
        round_state = answer_arena_question(
            round_state, question, question.correct_answer
        )

    summary = build_arena_summary(round_state, bank)
    assert summary.total_questions == 5
    assert summary.correct_count == 4
    assert summary.score == 40
    assert summary.max_score == 50
    assert summary.accuracy == 0.8
    assert summary.focus_vocabulary


def test_game_state_is_plain_memory_and_has_no_exam_or_database_dependency() -> None:
    bank = load_training_arena_bank()
    round_state = start_arena_round(bank, rng=random.Random(11))
    assert not hasattr(round_state, "user_id")
    assert "exam" not in type(round_state).__module__
    assert "database" not in type(round_state).__module__
    assert arena_round_key(1) != arena_round_key(2)
    with pytest.raises(ValueError, match="invalid_user"):
        arena_round_key(0)
