"""Pure summaries shared by Reading and Listening review views."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


class ReviewResult(Protocol):
    """Minimum deterministic fields required for exam-result aggregation."""

    question_type: str
    is_correct: bool
    user_answer: str


@dataclass(frozen=True)
class QuestionTypeAnalysis:
    """One question-type accuracy row for an exam result."""

    question_type: str
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        """Return the safe zero-to-one accuracy for this question type."""

        return self.correct / self.total if self.total else 0.0


def answer_status(result: ReviewResult) -> str:
    """Return the Chinese answer-card label for one deterministic result."""

    if not result.user_answer.strip():
        return "未作答"
    return "正确" if result.is_correct else "错误"


def build_question_type_analysis(
    results: Iterable[ReviewResult],
) -> tuple[QuestionTypeAnalysis, ...]:
    """Group exact answer outcomes by their existing bank question type."""

    grouped: dict[str, list[ReviewResult]] = {}
    for result in results:
        grouped.setdefault(result.question_type, []).append(result)
    return tuple(
        QuestionTypeAnalysis(
            question_type=question_type,
            correct=sum(item.is_correct for item in items),
            total=len(items),
        )
        for question_type, items in grouped.items()
    )
