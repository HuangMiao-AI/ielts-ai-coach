"""Validated access to project-original offline Listening mini tests."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from ielts_ai_coach.services.listening_models import (
    ListeningBank,
    ListeningQuestion,
    ListeningScriptTurn,
    ListeningSection,
    ListeningTest,
)
from ielts_ai_coach.services.review_content import build_question_review, build_vocabulary_items


BANK_PATH = (
    Path(__file__).resolve().parent.parent
    / "content"
    / "question_banks"
    / "listening_v1.json"
)
VALID_QUESTION_TYPES = {
    "multiple_choice",
    "form_completion",
    "note_completion",
}
VALID_SPEAKERS = {"Speaker A", "Speaker B", "Narrator"}


def _text(payload: dict[str, Any], field: str) -> str:
    """Read one required non-empty text value."""

    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value.strip()


def _question(
    payload: dict[str, Any],
    *,
    source_text: str,
) -> ListeningQuestion:
    """Validate one question and its scoring contract."""

    question_type = _text(payload, "question_type")
    if question_type not in VALID_QUESTION_TYPES:
        raise ValueError("invalid_question_type")
    raw_options = payload.get("options")
    if not isinstance(raw_options, list) or not all(
        isinstance(item, str) and item.strip() for item in raw_options
    ):
        raise ValueError("invalid_options")
    options = tuple(item.strip() for item in raw_options)
    if question_type == "multiple_choice" and len(options) < 3:
        raise ValueError("invalid_options")
    if question_type != "multiple_choice" and options:
        raise ValueError("invalid_options")
    answer = _text(payload, "correct_answer")
    if options and answer not in options:
        raise ValueError("answer_not_in_options")
    question_id = _text(payload, "question_id")
    question = _text(payload, "question")
    explanation = _text(payload, "explanation")
    evidence = _text(payload, "evidence")
    return ListeningQuestion(
        question_id=question_id,
        question_type=question_type,
        question=question,
        options=options,
        correct_answer=answer,
        explanation=explanation,
        evidence=evidence,
        review=build_question_review(
            question_id=question_id,
            question_type=question_type,
            question=question,
            correct_answer=answer,
            explanation=explanation,
            evidence=evidence,
            source_text=source_text,
        ),
    )


def _section(payload: dict[str, Any]) -> ListeningSection:
    """Validate one section with eight questions and voiced script."""

    raw_script = payload.get("script")
    raw_questions = payload.get("questions")
    if not isinstance(raw_script, list) or not raw_script:
        raise ValueError("invalid_script")
    if not isinstance(raw_questions, list) or len(raw_questions) != 8:
        raise ValueError("invalid_question_count")
    script = tuple(
        ListeningScriptTurn(
            speaker=_text(turn, "speaker"),
            text=_text(turn, "text"),
            pause_ms=int(turn.get("pause_ms", 0)),
        )
        for turn in raw_script
        if isinstance(turn, dict)
    )
    if len(script) != len(raw_script) or any(
        turn.speaker not in VALID_SPEAKERS
        or not 0 <= turn.pause_ms <= 5000
        for turn in script
    ):
        raise ValueError("invalid_script")
    source_text = " ".join(turn.text for turn in script)
    questions = tuple(
        _question(item, source_text=source_text)
        for item in raw_questions
        if isinstance(item, dict)
    )
    if len(questions) != len(raw_questions):
        raise ValueError("invalid_questions")
    section_id = _text(payload, "section_id")
    title = _text(payload, "title")
    scenario = _text(payload, "scenario")
    return ListeningSection(
        section_id=section_id,
        title=title,
        scenario=scenario,
        script=script,
        questions=questions,
        vocabulary_items=build_vocabulary_items(
            source_id=section_id,
            source_text=" ".join(
                (
                    title,
                    scenario,
                    source_text,
                    *(question.question for question in questions),
                    *(option for question in questions for option in question.options),
                    *(question.explanation for question in questions),
                    *(question.evidence for question in questions),
                )
            ),
        ),
    )


def _test(payload: dict[str, Any]) -> ListeningTest:
    """Validate one two-section mini test."""

    raw_sections = payload.get("sections")
    minutes = payload.get("estimated_minutes")
    if not isinstance(raw_sections, list) or len(raw_sections) != 2:
        raise ValueError("invalid_section_count")
    if not isinstance(minutes, int) or not 10 <= minutes <= 30:
        raise ValueError("invalid_estimated_minutes")
    sections = tuple(
        _section(item) for item in raw_sections if isinstance(item, dict)
    )
    test = ListeningTest(
        test_id=_text(payload, "test_id"),
        title=_text(payload, "title"),
        audio_path=_text(payload, "audio_path"),
        estimated_minutes=minutes,
        sections=sections,
    )
    if len(test.questions) != 16 or {
        question.question_type for question in test.questions
    } != VALID_QUESTION_TYPES:
        raise ValueError("invalid_test_questions")
    return test


@lru_cache(maxsize=1)
def load_listening_bank(path: Path | None = None) -> ListeningBank:
    """Load and strictly validate the bundled versioned Listening bank."""

    payload = json.loads((path or BANK_PATH).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid_bank")
    source = payload.get("source")
    raw_tests = payload.get("tests")
    if not isinstance(source, dict) or not isinstance(raw_tests, list):
        raise ValueError("invalid_bank")
    if (
        source.get("source_type") != "project_original"
        or source.get("is_official_ielts_content") is not False
        or len(raw_tests) != 2
    ):
        raise ValueError("invalid_source")
    tests = tuple(_test(item) for item in raw_tests if isinstance(item, dict))
    question_ids = [
        question.question_id for test in tests for question in test.questions
    ]
    section_ids = [
        section.section_id for test in tests for section in test.sections
    ]
    if (
        len(tests) != 2
        or len({test.test_id for test in tests}) != 2
        or len(question_ids) != len(set(question_ids))
        or len(section_ids) != len(set(section_ids))
    ):
        raise ValueError("duplicate_identifier")
    return ListeningBank(
        bank_id=_text(payload, "bank_id"),
        version=_text(payload, "version"),
        source_type=_text(source, "source_type"),
        source_name=_text(source, "source_name"),
        copyright_notice=_text(source, "copyright_notice"),
        is_official_ielts_content=False,
        tests=tests,
    )


def get_listening_test(test_id: str) -> ListeningTest:
    """Return one validated test by its stable identifier."""

    for test in load_listening_bank().tests:
        if test.test_id == test_id:
            return test
    raise KeyError("listening_test_not_found")
