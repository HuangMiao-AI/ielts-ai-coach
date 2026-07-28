"""Validated access to the bundled original IELTS reading question bank."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from ielts_ai_coach.services.question_models import (
    ReadingBank,
    ReadingPassage,
    ReadingQuestion,
    ReadingSection,
)
from ielts_ai_coach.services.review_content import build_question_review, build_vocabulary_items


BANK_PATH = (
    Path(__file__).resolve().parent.parent
    / "content"
    / "question_banks"
    / "reading_v1.json"
)
V2_BANK_PATH = BANK_PATH.with_name("reading_v2.json")
VALID_QUESTION_TYPES = {
    "multiple_choice",
    "true_false_not_given",
    "matching_heading",
}
READING_PASSAGE_IDS = ("AR-V1-001", "AR-V1-002", "AR-V1-003")


def _required_text(payload: dict[str, Any], field: str) -> str:
    """Read one required non-empty string from untrusted JSON."""

    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value.strip()


def _build_question(
    payload: dict[str, Any],
    *,
    source_text: str,
) -> ReadingQuestion:
    """Validate and construct one question."""

    question_type = _required_text(payload, "question_type")
    options = payload.get("options")
    if question_type not in VALID_QUESTION_TYPES:
        raise ValueError("invalid_question_type")
    if not isinstance(options, list) or len(options) < 3:
        raise ValueError("invalid_options")
    clean_options = tuple(
        item.strip()
        for item in options
        if isinstance(item, str) and item.strip()
    )
    if len(clean_options) != len(options) or len(set(clean_options)) != len(options):
        raise ValueError("invalid_options")
    correct_answer = _required_text(payload, "correct_answer")
    if correct_answer not in clean_options:
        raise ValueError("answer_not_in_options")
    question_id = _required_text(payload, "question_id")
    question = _required_text(payload, "question")
    explanation = _required_text(payload, "explanation")
    evidence = _required_text(payload, "evidence")
    return ReadingQuestion(
        question_id=question_id,
        question_type=question_type,
        question=question,
        options=clean_options,
        correct_answer=correct_answer,
        explanation=explanation,
        evidence=evidence,
        review=build_question_review(
            question_id=question_id,
            question_type=question_type,
            question=question,
            correct_answer=correct_answer,
            explanation=explanation,
            evidence=evidence,
            source_text=source_text,
        ),
    )


def _build_passage(
    payload: dict[str, Any],
    *,
    version: str,
    source: dict[str, Any],
    word_range: tuple[int, int],
    question_range: tuple[int, int],
) -> ReadingPassage:
    """Validate and construct one passage."""

    raw_sections = payload.get("sections")
    raw_questions = payload.get("questions")
    if not isinstance(raw_sections, list) or len(raw_sections) < 5:
        raise ValueError("invalid_sections")
    if (
        not isinstance(raw_questions, list)
        or not question_range[0] <= len(raw_questions) <= question_range[1]
    ):
        raise ValueError("invalid_question_count")
    sections = tuple(
        ReadingSection(
            label=_required_text(section, "label"),
            text=_required_text(section, "text"),
        )
        for section in raw_sections
        if isinstance(section, dict)
    )
    source_text = " ".join(section.text for section in sections)
    questions = tuple(
        _build_question(question, source_text=source_text)
        for question in raw_questions
        if isinstance(question, dict)
    )
    if len(sections) != len(raw_sections) or len(questions) != len(raw_questions):
        raise ValueError("invalid_passage_items")
    passage_id = _required_text(payload, "passage_id")
    passage = ReadingPassage(
        passage_id=passage_id,
        version=version,
        title=_required_text(payload, "title"),
        recommended_minutes=_required_recommended_minutes(payload),
        sections=sections,
        questions=questions,
        vocabulary_items=build_vocabulary_items(
            source_id=passage_id,
            source_text=" ".join(
                (
                    source_text,
                    *(question.question for question in questions),
                    *(option for question in questions for option in question.options),
                    *(question.explanation for question in questions),
                    *(question.evidence for question in questions),
                )
            ),
        ),
        topic=str(payload.get("topic", "Academic Skills")).strip()
        or "Academic Skills",
        source_type=_required_text(source, "source_type"),
        source_name=_required_text(source, "source_name"),
        copyright_notice=_required_text(source, "copyright_notice"),
        is_official_ielts_content=source.get("is_official_ielts_content") is True,
    )
    if not word_range[0] <= passage.word_count <= word_range[1]:
        raise ValueError("invalid_passage_word_count")
    if {question.question_type for question in questions} != VALID_QUESTION_TYPES:
        raise ValueError("missing_question_type")
    return passage


def _required_recommended_minutes(payload: dict[str, Any]) -> int:
    """Read the author-set, bounded duration for one original passage."""

    value = payload.get("recommended_minutes")
    if not isinstance(value, int) or isinstance(value, bool) or not 10 <= value <= 40:
        raise ValueError("invalid_recommended_minutes")
    return value


def load_reading_bank(path: Path | None = None) -> ReadingBank:
    """Load and validate the versioned project-original reading bank."""

    source_path = path or BANK_PATH
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid_bank")
    source = payload.get("source")
    raw_passages = payload.get("passages")
    if not isinstance(source, dict) or not isinstance(raw_passages, list):
        raise ValueError("invalid_bank")
    if (
        source.get("source_type") != "project_original"
        or source.get("is_official_ielts_content") is not False
    ):
        raise ValueError("invalid_source")
    version = _required_text(payload, "version")
    is_v2 = version.startswith("2.")
    word_range = (750, 950) if is_v2 else (800, 1000)
    question_range = (10, 10) if is_v2 else (8, 10)
    passages = tuple(
        _build_passage(
            item,
            version=version,
            source=source,
            word_range=word_range,
            question_range=question_range,
        )
        for item in raw_passages
        if isinstance(item, dict)
    )
    passage_ids = [passage.passage_id for passage in passages]
    question_ids = [
        question.question_id
        for passage in passages
        for question in passage.questions
    ]
    expected_ids = (
        tuple(f"AR-V2-{index:03d}" for index in range(1, 6))
        if is_v2
        else READING_PASSAGE_IDS
    )
    if tuple(passage_ids) != expected_ids or len(set(question_ids)) != len(
        question_ids
    ):
        raise ValueError("invalid_bank_identifiers")
    return ReadingBank(
        bank_id=_required_text(payload, "bank_id"),
        version=version,
        passages=passages,
    )


@lru_cache(maxsize=1)
def get_reading_bank() -> ReadingBank:
    """Return the validated bundled bank without repeated disk reads."""

    return load_reading_bank()


@lru_cache(maxsize=1)
def load_reading_catalog() -> tuple[ReadingPassage, ...]:
    """Return v1 and v2 original passages in stable release order."""

    v1 = get_reading_bank().passages
    v2 = load_reading_bank(V2_BANK_PATH).passages
    passages = (*v1, *v2)
    question_ids = [
        question.question_id
        for passage in passages
        for question in passage.questions
    ]
    if (
        len({passage.passage_id for passage in passages}) != len(passages)
        or len(set(question_ids)) != len(question_ids)
    ):
        raise ValueError("duplicate_catalog_identifier")
    return passages


def get_reading_passage(passage_id: str) -> ReadingPassage:
    """Return one passage by stable identifier."""

    for passage in load_reading_catalog():
        if passage.passage_id == passage_id:
            return passage
    raise KeyError("reading_passage_not_found")


def select_reading_passage(
    *,
    preferred_id: str = "",
    task_id: int = 0,
) -> ReadingPassage:
    """Choose a stable passage for new or existing structured tasks."""

    if preferred_id:
        return get_reading_passage(preferred_id)
    index = max(task_id - 1, 0) % len(READING_PASSAGE_IDS)
    return get_reading_passage(READING_PASSAGE_IDS[index])
