"""Validated local vocabulary and deterministic Listening spelling rules."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import random
import re
from typing import Any

from ielts_ai_coach.services.listening_vocabulary_models import (
    LearningSession,
    SpellingAttempt,
    SpellingSession,
    SpellingSummary,
    VocabularyBank,
    VocabularyEntry,
)


VOCABULARY_PATH = (
    Path(__file__).resolve().parent.parent
    / "content"
    / "question_banks"
    / "listening_vocabulary_v1.json"
)
VOCABULARY_CATEGORIES = {
    "Academic English",
    "Education",
    "Environment",
    "Technology",
    "Health",
    "Society",
    "Economy",
    "Work",
    "Travel",
    "Science",
    "Culture",
}
VOCABULARY_LEVELS = {"B1", "B2", "C1"}
PARTS_OF_SPEECH = {
    "adjective",
    "adverb",
    "noun",
    "verb",
}
GROUP_SIZE = 10
_ID_PATTERN = re.compile(r"^vocab_[0-9]{3,}$")
_WORD_PATTERN = re.compile(r"^[a-z]+$")


def _required_text(payload: dict[str, Any], field: str) -> str:
    """Read one required non-empty text value."""

    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value.strip()


@lru_cache(maxsize=1)
def load_vocabulary_bank(path: Path | None = None) -> VocabularyBank:
    """Load and strictly validate the project-curated static vocabulary bank."""

    payload = json.loads((path or VOCABULARY_PATH).read_text(encoding="utf-8"))
    raw_entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(raw_entries, list) or len(raw_entries) < 300:
        raise ValueError("invalid_vocabulary_coverage")
    entries: list[VocabularyEntry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            raise ValueError("invalid_vocabulary_entry")
        entry_id = _required_text(item, "id")
        word = _required_text(item, "word")
        meaning = _required_text(item, "meaning_zh")
        part = _required_text(item, "part_of_speech")
        level = _required_text(item, "level")
        category = _required_text(item, "category")
        if (
            not _ID_PATTERN.fullmatch(entry_id)
            or not _WORD_PATTERN.fullmatch(word)
            or part not in PARTS_OF_SPEECH
            or level not in VOCABULARY_LEVELS
            or category not in VOCABULARY_CATEGORIES
        ):
            raise ValueError("invalid_vocabulary_entry")
        entries.append(
            VocabularyEntry(entry_id, word, meaning, part, level, category)
        )
    ids = [entry.entry_id for entry in entries]
    words = [entry.word.casefold() for entry in entries]
    if len(ids) != len(set(ids)) or len(words) != len(set(words)):
        raise ValueError("duplicate_vocabulary_entry")
    return VocabularyBank(
        bank_id=_required_text(payload, "bank_id"),
        version=_required_text(payload, "version"),
        source_type=_required_text(payload, "source_type"),
        entries=tuple(entries),
    )


def _validated_ids(bank: VocabularyBank, word_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Validate a non-empty, unique subset against the current bank."""

    if not word_ids or len(word_ids) != len(set(word_ids)):
        raise ValueError("invalid_word_group")
    if any(word_id not in bank.by_id for word_id in word_ids):
        raise ValueError("unknown_word")
    return word_ids


def valid_learning_session(session: object, bank: VocabularyBank) -> bool:
    """Return whether a restored learning session is safe to render."""

    if not isinstance(session, LearningSession):
        return False
    try:
        _validated_ids(bank, session.word_ids)
    except ValueError:
        return False
    if not 0 <= session.current_index < len(session.word_ids):
        return False
    if session.completed and session.current_index != len(session.word_ids) - 1:
        return False
    return not session.completion_recorded or session.completed


def valid_spelling_session(session: object, bank: VocabularyBank) -> bool:
    """Return whether restored spelling progress is internally consistent."""

    if not isinstance(session, SpellingSession) or len(session.word_ids) != GROUP_SIZE:
        return False
    try:
        _validated_ids(bank, session.word_ids)
    except ValueError:
        return False
    if not 0 <= session.current_index < len(session.word_ids):
        return False
    if len(session.attempts) not in {session.current_index, session.current_index + 1}:
        return False
    if any(
        attempt.word_id != session.word_ids[index]
        for index, attempt in enumerate(session.attempts)
    ):
        return False
    if session.correct_count != sum(attempt.correct for attempt in session.attempts):
        return False
    if session.completed:
        return (
            session.current_index == len(session.word_ids) - 1
            and len(session.attempts) == len(session.word_ids)
        )
    return True


def start_learning(
    bank: VocabularyBank,
    *,
    rng: random.Random | random.SystemRandom | None = None,
    word_ids: tuple[str, ...] | None = None,
) -> LearningSession:
    """Start a unique ten-word group or an exact short review group."""

    if word_ids is None:
        chooser = rng or random.SystemRandom()
        word_ids = tuple(
            entry.entry_id for entry in chooser.sample(list(bank.entries), GROUP_SIZE)
        )
    return LearningSession(word_ids=_validated_ids(bank, tuple(word_ids)))


def advance_learning(session: LearningSession) -> LearningSession:
    """Move to the next word or finish after the final word."""

    if session.completed:
        raise ValueError("learning_completed")
    is_last = session.current_index == len(session.word_ids) - 1
    return LearningSession(
        word_ids=session.word_ids,
        current_index=session.current_index if is_last else session.current_index + 1,
        completed=is_last,
        completion_recorded=session.completion_recorded,
    )


def start_spelling(
    bank: VocabularyBank,
    *,
    recent_word_ids: tuple[str, ...] | None = None,
    rng: random.Random | random.SystemRandom | None = None,
) -> SpellingSession:
    """Start ten unique spelling targets, preferring a completed study group."""

    if recent_word_ids is not None and len(recent_word_ids) == GROUP_SIZE:
        word_ids = _validated_ids(bank, tuple(recent_word_ids))
    else:
        chooser = rng or random.SystemRandom()
        word_ids = tuple(
            entry.entry_id for entry in chooser.sample(list(bank.entries), GROUP_SIZE)
        )
    return SpellingSession(word_ids=word_ids)


def normalize_spelling_answer(answer: str) -> str:
    """Apply only the documented case and surrounding-space normalization."""

    return answer.strip().casefold()


def submit_spelling_answer(
    session: SpellingSession,
    bank: VocabularyBank,
    answer: str,
) -> SpellingSession:
    """Lock and score the current answer exactly once."""

    if session.completed:
        raise ValueError("spelling_completed")
    if session.awaiting_advance:
        raise ValueError("question_already_submitted")
    entry = bank.by_id[session.current_word_id]
    normalized = normalize_spelling_answer(answer)
    correct = normalized == entry.word
    attempt = SpellingAttempt(entry.entry_id, normalized, correct)
    return SpellingSession(
        word_ids=session.word_ids,
        current_index=session.current_index,
        attempts=(*session.attempts, attempt),
        correct_count=session.correct_count + int(correct),
    )


def advance_spelling(session: SpellingSession) -> SpellingSession:
    """Leave feedback and move forward, completing after question ten."""

    if not session.awaiting_advance:
        raise ValueError("submitted_answer_required")
    is_last = session.current_index == len(session.word_ids) - 1
    return SpellingSession(
        word_ids=session.word_ids,
        current_index=session.current_index if is_last else session.current_index + 1,
        attempts=session.attempts,
        correct_count=session.correct_count,
        completed=is_last,
    )


def build_spelling_summary(session: SpellingSession) -> SpellingSummary:
    """Build exact metrics only after all questions are complete."""

    if not session.completed:
        raise ValueError("spelling_not_completed")
    total = len(session.word_ids)
    return SpellingSummary(
        correct_count=session.correct_count,
        total_questions=total,
        accuracy=session.correct_count / total,
        score=session.score,
        max_score=total * 10,
        wrong_word_ids=session.wrong_word_ids,
    )
