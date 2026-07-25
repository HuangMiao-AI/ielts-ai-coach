"""Pure deterministic scoring for original Listening mini tests."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from ielts_ai_coach.services.listening_bank import ListeningTest


@dataclass(frozen=True)
class ListeningQuestionResult:
    """One answer outcome with review evidence."""

    question_id: str
    question: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    evidence: str


@dataclass(frozen=True)
class ListeningScore:
    """Complete deterministic result for one mini test."""

    test_id: str
    test_title: str
    correct_count: int
    total_questions: int
    accuracy: float
    results: tuple[ListeningQuestionResult, ...]


def normalize_listening_answer(value: str) -> str:
    """Normalize case and repeated whitespace without changing content."""

    return re.sub(r"\s+", " ", value.strip()).casefold()


def score_listening_answers(
    test: ListeningTest,
    answers: Mapping[str, str],
) -> ListeningScore:
    """Require all answers and return deterministic per-question results."""

    expected_ids = {question.question_id for question in test.questions}
    if set(answers) != expected_ids or any(
        not isinstance(answer, str) or not normalize_listening_answer(answer)
        for answer in answers.values()
    ):
        raise ValueError("incomplete_answers")
    results = tuple(
        ListeningQuestionResult(
            question_id=question.question_id,
            question=question.question,
            user_answer=answers[question.question_id].strip(),
            correct_answer=question.correct_answer,
            is_correct=(
                normalize_listening_answer(answers[question.question_id])
                == normalize_listening_answer(question.correct_answer)
            ),
            explanation=question.explanation,
            evidence=question.evidence,
        )
        for question in test.questions
    )
    correct = sum(result.is_correct for result in results)
    return ListeningScore(
        test_id=test.test_id,
        test_title=test.title,
        correct_count=correct,
        total_questions=len(results),
        accuracy=correct / len(results),
        results=results,
    )
