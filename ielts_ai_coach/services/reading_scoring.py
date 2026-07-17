"""Pure deterministic scoring for original reading practice."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import unicodedata
from typing import Mapping

from ielts_ai_coach.services.question_bank import ReadingPassage


@dataclass(frozen=True)
class ReadingQuestionResult:
    """The persisted review result for one question."""

    question_id: str
    question_type: str
    question: str
    options: tuple[str, ...]
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    evidence: str


@dataclass(frozen=True)
class ReadingScore:
    """Complete deterministic score and review snapshot."""

    passage_id: str
    passage_version: str
    passage_title: str
    correct_count: int
    total_questions: int
    accuracy: float
    results: tuple[ReadingQuestionResult, ...]

    @property
    def incorrect_question_ids(self) -> tuple[str, ...]:
        """Return stable identifiers for every incorrect answer."""

        return tuple(
            result.question_id for result in self.results if not result.is_correct
        )


def normalize_answer(value: str) -> str:
    """Normalize Unicode, repeated whitespace, and case for comparison."""

    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split()).casefold()


def score_reading_answers(
    passage: ReadingPassage,
    answers: Mapping[str, str],
) -> ReadingScore:
    """Score every passage question without AI or network access."""

    expected_ids = {question.question_id for question in passage.questions}
    if set(answers) - expected_ids:
        raise ValueError("unknown_question_id")
    results = []
    for question in passage.questions:
        user_answer = answers.get(question.question_id, "")
        is_correct = normalize_answer(user_answer) == normalize_answer(
            question.correct_answer
        )
        results.append(
            ReadingQuestionResult(
                question_id=question.question_id,
                question_type=question.question_type,
                question=question.question,
                options=question.options,
                user_answer=user_answer.strip(),
                correct_answer=question.correct_answer,
                is_correct=is_correct,
                explanation=question.explanation,
                evidence=question.evidence,
            )
        )
    correct_count = sum(result.is_correct for result in results)
    total_questions = len(results)
    return ReadingScore(
        passage_id=passage.passage_id,
        passage_version=passage.version,
        passage_title=passage.title,
        correct_count=correct_count,
        total_questions=total_questions,
        accuracy=correct_count / total_questions if total_questions else 0.0,
        results=tuple(results),
    )


def serialize_reading_score(score: ReadingScore) -> str:
    """Serialize a complete review snapshot for durable history."""

    return json.dumps(
        asdict(score),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def deserialize_reading_score(payload: str) -> ReadingScore:
    """Restore a validated-enough internal score snapshot from storage."""

    data = json.loads(payload)
    raw_results = data.get("results", [])
    results = tuple(
        ReadingQuestionResult(
            question_id=str(item["question_id"]),
            question_type=str(item["question_type"]),
            question=str(item["question"]),
            options=tuple(str(option) for option in item["options"]),
            user_answer=str(item["user_answer"]),
            correct_answer=str(item["correct_answer"]),
            is_correct=item["is_correct"] is True,
            explanation=str(item["explanation"]),
            evidence=str(item["evidence"]),
        )
        for item in raw_results
    )
    return ReadingScore(
        passage_id=str(data["passage_id"]),
        passage_version=str(data["passage_version"]),
        passage_title=str(data["passage_title"]),
        correct_count=int(data["correct_count"]),
        total_questions=int(data["total_questions"]),
        accuracy=float(data["accuracy"]),
        results=results,
    )
