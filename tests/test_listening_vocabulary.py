"""Deterministic contracts for the session-only Listening vocabulary trainer."""

from __future__ import annotations

import random

import pytest

from ielts_ai_coach.services.listening_vocabulary import (
    VOCABULARY_CATEGORIES,
    advance_learning,
    advance_spelling,
    build_spelling_summary,
    load_vocabulary_bank,
    normalize_spelling_answer,
    start_learning,
    start_spelling,
    submit_spelling_answer,
    valid_learning_session,
    valid_spelling_session,
)
from ielts_ai_coach.services.listening_vocabulary_models import (
    LearningSession,
    SpellingSession,
)


def test_curated_vocabulary_bank_has_300_valid_unique_entries() -> None:
    """The local bank must be large, extensible, and mechanically trustworthy."""

    bank = load_vocabulary_bank()

    assert bank.source_type == "project_curated"
    assert len(bank.entries) == 300
    assert len({entry.entry_id for entry in bank.entries}) == 300
    assert len({entry.word.casefold() for entry in bank.entries}) == 300
    assert {entry.category for entry in bank.entries} == VOCABULARY_CATEGORIES
    assert all(entry.word and entry.meaning_zh and entry.part_of_speech for entry in bank.entries)
    assert all(entry.level in {"B1", "B2", "C1"} for entry in bank.entries)
    assert all(entry.word.isalpha() and entry.word.isascii() for entry in bank.entries)
    assert all(entry.word == entry.word.casefold() for entry in bank.entries)
    obvious_homophones = {"cell", "gene", "principle", "profit", "source", "tax", "waste"}
    assert not obvious_homophones.intersection(entry.word for entry in bank.entries)


def test_learning_defaults_to_ten_unique_words_and_completes() -> None:
    """A normal learning group contains ten unique items and finishes safely."""

    bank = load_vocabulary_bank()
    session = start_learning(bank, rng=random.Random(7))

    assert len(session.word_ids) == 10
    assert len(set(session.word_ids)) == 10
    for _ in range(10):
        session = advance_learning(session)
    assert session.completed is True
    assert session.current_index == 9


def test_spelling_prefers_recent_learning_and_has_no_duplicates() -> None:
    """The just-learned group becomes the next ten-question spelling round."""

    bank = load_vocabulary_bank()
    learned = start_learning(bank, rng=random.Random(3)).word_ids
    spelling = start_spelling(bank, recent_word_ids=learned, rng=random.Random(9))

    assert spelling.word_ids == learned
    assert len(set(spelling.word_ids)) == 10


def test_spelling_without_learning_history_selects_ten_unique_words() -> None:
    """A learner can start spelling directly from the full bank."""

    spelling = start_spelling(load_vocabulary_bank(), rng=random.Random(11))

    assert len(spelling.word_ids) == 10
    assert len(set(spelling.word_ids)) == 10


def test_answer_normalization_is_only_casefold_and_outer_whitespace() -> None:
    """Scoring accepts case and edge whitespace but not misspellings."""

    assert normalize_spelling_answer(" Environment ") == "environment"
    assert normalize_spelling_answer("enviroment") != "environment"


def test_each_spelling_question_scores_once() -> None:
    """Repeated submission cannot add score or correct count twice."""

    bank = load_vocabulary_bank()
    session = start_spelling(bank, rng=random.Random(13))
    answer = bank.by_id[session.word_ids[0]].word

    submitted = submit_spelling_answer(session, bank, f" {answer.upper()} ")

    assert submitted.correct_count == 1
    assert submitted.score == 10
    assert submitted.awaiting_advance is True
    with pytest.raises(ValueError, match="question_already_submitted"):
        submit_spelling_answer(submitted, bank, answer)


def test_incorrect_answer_scores_zero_and_is_listed_for_review() -> None:
    """Wrong answers remain deterministic and feed the review list."""

    bank = load_vocabulary_bank()
    session = start_spelling(bank, rng=random.Random(17))
    expected_id = session.word_ids[0]
    submitted = submit_spelling_answer(session, bank, "definitelywrong")

    assert submitted.correct_count == 0
    assert submitted.score == 0
    assert submitted.attempts[0].word_id == expected_id
    assert submitted.attempts[0].correct is False


def test_spelling_round_summary_and_reset_are_correct() -> None:
    """Ten locked answers produce exact final metrics and a clean next round."""

    bank = load_vocabulary_bank()
    session = start_spelling(bank, rng=random.Random(19))
    for index in range(10):
        expected = bank.by_id[session.word_ids[session.current_index]].word
        answer = expected if index < 8 else "wrong"
        session = submit_spelling_answer(session, bank, answer)
        session = advance_spelling(session)

    summary = build_spelling_summary(session)
    assert summary.correct_count == 8
    assert summary.total_questions == 10
    assert summary.accuracy == 0.8
    assert summary.score == 80
    assert summary.max_score == 100
    assert summary.wrong_word_ids == session.word_ids[-2:]

    replay = start_spelling(bank, rng=random.Random(23))
    assert replay.current_index == 0
    assert replay.attempts == ()
    assert replay.correct_count == 0
    assert replay.completed is False


def test_wrong_words_can_start_a_short_review_learning_group() -> None:
    """Review mode accepts only the wrong IDs and never pads the group."""

    bank = load_vocabulary_bank()
    wrong_ids = tuple(entry.entry_id for entry in bank.entries[:3])
    review = start_learning(bank, word_ids=wrong_ids)

    assert review.word_ids == wrong_ids
    assert len(review.word_ids) == 3


def test_stale_or_corrupt_session_shapes_are_rejected_before_rendering() -> None:
    """Bad indices and unknown IDs cannot reach page indexing operations."""

    bank = load_vocabulary_bank()

    assert valid_learning_session(
        LearningSession(word_ids=(bank.entries[0].entry_id,), current_index=9), bank
    ) is False
    assert valid_learning_session(
        LearningSession(word_ids=("missing",)), bank
    ) is False
    assert valid_spelling_session(
        SpellingSession(word_ids=tuple(entry.entry_id for entry in bank.entries[:9])), bank
    ) is False
    assert valid_spelling_session(
        SpellingSession(
            word_ids=tuple(entry.entry_id for entry in bank.entries[:10]),
            current_index=9,
            attempts=(),
        ),
        bank,
    ) is False
