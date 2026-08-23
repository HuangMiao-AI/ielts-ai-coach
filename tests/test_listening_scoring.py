"""Deterministic Listening scoring and transient-state isolation."""

from __future__ import annotations

import pytest

from ielts_ai_coach.services.listening_bank import load_listening_bank
from ielts_ai_coach.services.listening_scoring import (
    score_listening_answers,
)
from ielts_ai_coach.services.listening_session import (
    listening_answer_key,
    listening_result_key,
    listening_session_key,
)


def test_listening_scoring_normalizes_case_and_spaces() -> None:
    """Text answers are case-insensitive and collapse surrounding whitespace."""

    test = load_listening_bank().tests[0]
    answers = {
        question.question_id: f"  {question.correct_answer.swapcase()}  "
        for question in test.questions
    }

    score = score_listening_answers(test, answers)

    assert score.correct_count == 6
    assert score.total_questions == 6
    assert score.accuracy == 1.0
    assert all(result.is_correct for result in score.results)


def test_listening_scoring_requires_every_answer_and_reports_errors() -> None:
    """Incomplete submissions fail and wrong answers retain full review data."""

    test = load_listening_bank().tests[1]
    incomplete = {
        question.question_id: question.correct_answer
        for question in test.questions[:-1]
    }
    with pytest.raises(ValueError, match="incomplete_answers"):
        score_listening_answers(test, incomplete)

    answers = {
        question.question_id: question.correct_answer
        for question in test.questions
    }
    answers[test.questions[0].question_id] = "definitely wrong"
    score = score_listening_answers(test, answers)

    assert score.correct_count == 5
    first = score.results[0]
    assert first.is_correct is False
    assert first.correct_answer == test.questions[0].correct_answer
    assert first.explanation
    assert first.evidence


def test_listening_timeout_scores_unanswered_items_as_incorrect() -> None:
    """The explicit timeout path may score missing answers as blank."""

    test = load_listening_bank().tests[0]
    answers = {
        question.question_id: question.correct_answer
        for question in test.questions[1:]
    }

    score = score_listening_answers(
        test,
        answers,
        allow_incomplete=True,
    )

    assert score.correct_count == score.total_questions - 1
    assert score.results[0].user_answer == ""
    assert score.results[0].is_correct is False


def test_listening_session_keys_are_user_and_test_scoped() -> None:
    """Transient Listening answers and results never share a user's namespace."""

    assert listening_session_key(1, "LISTEN-V1-001") != listening_session_key(
        2, "LISTEN-V1-001"
    )
    assert listening_answer_key(1, "LISTEN-V1-001") != listening_answer_key(
        1, "LISTEN-V1-002"
    )
    assert listening_result_key(1, "LISTEN-V1-001") != listening_result_key(
        2, "LISTEN-V1-001"
    )
