"""Immutable state models for Listening vocabulary learning and spelling."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class VocabularyEntry:
    """One unambiguous English spelling target with Chinese metadata."""

    entry_id: str
    word: str
    meaning_zh: str
    part_of_speech: str
    level: str
    category: str


@dataclass(frozen=True)
class VocabularyBank:
    """Versioned project-curated local vocabulary collection."""

    bank_id: str
    version: str
    source_type: str
    entries: tuple[VocabularyEntry, ...]

    @cached_property
    def by_id(self) -> dict[str, VocabularyEntry]:
        """Index entries by their stable IDs."""

        return {entry.entry_id: entry for entry in self.entries}


@dataclass(frozen=True)
class LearningSession:
    """Minimal current-session progress through one vocabulary group."""

    word_ids: tuple[str, ...]
    current_index: int = 0
    completed: bool = False
    completion_recorded: bool = False

    @property
    def current_word_id(self) -> str:
        """Return the active word ID while the session is open."""

        if self.completed:
            raise ValueError("learning_completed")
        return self.word_ids[self.current_index]


@dataclass(frozen=True)
class SpellingAttempt:
    """One locked spelling answer."""

    word_id: str
    answer: str
    correct: bool


@dataclass(frozen=True)
class SpellingSession:
    """Deterministic ten-question spelling state."""

    word_ids: tuple[str, ...]
    current_index: int = 0
    attempts: tuple[SpellingAttempt, ...] = ()
    correct_count: int = 0
    completed: bool = False

    @property
    def score(self) -> int:
        """Return ten points per correct answer."""

        return self.correct_count * 10

    @property
    def awaiting_advance(self) -> bool:
        """Return whether the current answer is already locked."""

        return not self.completed and len(self.attempts) == self.current_index + 1

    @property
    def current_word_id(self) -> str:
        """Return the active spelling target ID."""

        if self.completed:
            raise ValueError("spelling_completed")
        return self.word_ids[self.current_index]

    @property
    def wrong_word_ids(self) -> tuple[str, ...]:
        """Return wrong targets in round order."""

        return tuple(attempt.word_id for attempt in self.attempts if not attempt.correct)


@dataclass(frozen=True)
class SpellingSummary:
    """Exact final metrics for one completed spelling round."""

    correct_count: int
    total_questions: int
    accuracy: float
    score: int
    max_score: int
    wrong_word_ids: tuple[str, ...]
