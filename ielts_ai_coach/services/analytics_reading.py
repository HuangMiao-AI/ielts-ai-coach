"""Reading-only aggregate helpers for the analytics service."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ielts_ai_coach.services.reading_scoring import deserialize_reading_score


@dataclass(frozen=True)
class ReadingAnalytics:
    """Aggregate deterministic Reading-practice evidence."""

    attempt_count: int
    correct: int
    total: int
    accuracy: float | None
    error_counts: tuple[tuple[str, int], ...]
    frequent_error_types: tuple[str, ...]
    warnings: tuple[str, ...]


def build_reading_analytics(attempts: list[object]) -> ReadingAnalytics:
    """Aggregate persisted Reading totals and safe snapshot metadata."""

    correct = sum(int(attempt.score) for attempt in attempts)  # type: ignore[attr-defined]
    total = sum(int(attempt.total_questions) for attempt in attempts)  # type: ignore[attr-defined]
    errors: Counter[str] = Counter()
    warnings: set[str] = set()
    for attempt in attempts:
        try:
            snapshot = deserialize_reading_score(attempt.results_json)  # type: ignore[attr-defined]
        except (AttributeError, KeyError, TypeError, ValueError):
            warnings.add("invalid_reading_snapshot")
            continue
        errors.update(
            result.question_type
            for result in snapshot.results
            if not result.is_correct
        )
    error_counts = tuple(
        sorted(errors.items(), key=lambda item: (-item[1], item[0]))
    )
    highest_error_count = error_counts[0][1] if error_counts else 0
    frequent_error_types = (
        tuple(
            question_type
            for question_type, count in error_counts
            if count == highest_error_count
        )
        if highest_error_count >= 2
        else ()
    )
    return ReadingAnalytics(
        attempt_count=len(attempts),
        correct=correct,
        total=total,
        accuracy=correct / total if total else None,
        error_counts=error_counts,
        frequent_error_types=frequent_error_types,
        warnings=tuple(sorted(warnings)),
    )
