"""Tests for deterministic reading answer normalization and feedback."""

from __future__ import annotations

import pytest

from ielts_ai_coach.services.question_bank import get_reading_bank
from ielts_ai_coach.services.reading_scoring import score_reading_answers


def _spaced_lower(value: str) -> str:
    """Return an equivalent answer with changed case and repeated spaces."""

    return f"  {'   '.join(value.lower().split())}  "


def test_scoring_normalizes_case_and_whitespace() -> None:
    """Equivalent selected answers must receive a full deterministic score."""

    passage = get_reading_bank().passages[0]
    answers = {
        question.question_id: _spaced_lower(question.correct_answer)
        for question in passage.questions
    }

    score = score_reading_answers(passage, answers)

    assert score.correct_count == score.total_questions == 9
    assert score.accuracy == 1.0
    assert score.incorrect_question_ids == ()


def test_scoring_returns_wrong_answer_feedback_and_evidence() -> None:
    """Incorrect answers must retain the answer key, explanation, and evidence."""

    passage = get_reading_bank().passages[1]
    answers = {
        question.question_id: next(
            option
            for option in question.options
            if option != question.correct_answer
        )
        for question in passage.questions
    }
    first = passage.questions[0]
    answers[first.question_id] = first.correct_answer

    score = score_reading_answers(passage, answers)

    assert score.correct_count == 1
    assert score.accuracy == pytest.approx(1 / 9)
    assert len(score.incorrect_question_ids) == 8
    wrong_result = score.results[1]
    assert not wrong_result.is_correct
    assert wrong_result.user_answer
    assert wrong_result.correct_answer
    assert wrong_result.explanation
    assert wrong_result.evidence


def test_scoring_rejects_unknown_question_ids() -> None:
    """A submitted answer cannot target a question outside the passage."""

    passage = get_reading_bank().passages[2]

    with pytest.raises(ValueError, match="unknown_question_id"):
        score_reading_answers(passage, {"unknown": "True"})
