"""Contracts for Chinese-first, source-backed exam review content."""

from __future__ import annotations

import re

from ielts_ai_coach.services.listening_bank import load_listening_bank
from ielts_ai_coach.services.listening_scoring import score_listening_answers
from ielts_ai_coach.services.question_bank import load_reading_catalog
from ielts_ai_coach.services.reading_scoring import score_reading_answers


CHINESE = re.compile(r"[\u4e00-\u9fff]")


def _assert_question_review(question: object) -> None:
    """Require all source-backed fields shown in a student review."""

    assert CHINESE.search(question.explanation_zh)
    assert CHINESE.search(question.evidence_translation_zh)
    assert CHINESE.search(question.tested_skill)
    assert CHINESE.search(question.common_mistake_zh)
    assert question.evidence_text
    assert question.synonym_pairs


def _assert_vocabulary(items: tuple[object, ...]) -> None:
    """Require one deduplicated bilingual vocabulary list per source unit."""

    assert 8 <= len(items) <= 15
    assert len({item.word_or_phrase.casefold() for item in items}) == len(items)
    for item in items:
        assert item.part_of_speech
        assert CHINESE.search(item.meaning_zh)
        assert item.meaning_en
        assert item.source_context
        assert item.synonym_or_paraphrase
        assert CHINESE.search(item.ielts_note_zh)


def test_every_reading_question_and_passage_has_chinese_review_content() -> None:
    """All answerable Reading items must be reviewable without English-only copy."""

    passages = load_reading_catalog()

    assert len(passages) == 8
    for passage in passages:
        _assert_vocabulary(passage.vocabulary_items)
        passage_text = " ".join(section.text for section in passage.sections)
        for question in passage.questions:
            _assert_question_review(question)
            assert question.evidence_text in passage_text


def test_every_listening_question_and_script_section_has_chinese_review_content() -> None:
    """All answerable Listening items need verified-script evidence and vocabulary."""

    bank = load_listening_bank()

    for test in bank.tests:
        for section in test.sections:
            _assert_vocabulary(section.vocabulary_items)
            script_text = " ".join(turn.text for turn in section.script)
            for question in section.questions:
                _assert_question_review(question)
                assert question.evidence_text in script_text


def test_scoring_snapshots_retain_chinese_review_fields() -> None:
    """Submitted review snapshots must not fall back to English-only content."""

    passage = load_reading_catalog()[0]
    reading = score_reading_answers(
        passage,
        {question.question_id: question.correct_answer for question in passage.questions},
    )
    listening_test = load_listening_bank().tests[0]
    listening = score_listening_answers(
        listening_test,
        {
            question.question_id: question.correct_answer
            for question in listening_test.questions
        },
    )

    assert CHINESE.search(reading.results[0].explanation_zh)
    assert reading.results[0].evidence_text
    assert CHINESE.search(listening.results[0].explanation_zh)
    assert listening.results[0].evidence_translation_zh
