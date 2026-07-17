"""Validated access to the bundled original IELTS reading question bank."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any


BANK_PATH = (
    Path(__file__).resolve().parent.parent
    / "content"
    / "question_banks"
    / "reading_v1.json"
)
VALID_QUESTION_TYPES = {
    "multiple_choice",
    "true_false_not_given",
    "matching_heading",
}
READING_PASSAGE_IDS = ("AR-V1-001", "AR-V1-002", "AR-V1-003")


@dataclass(frozen=True)
class ReadingSection:
    """One labelled section of an original academic reading passage."""

    label: str
    text: str


@dataclass(frozen=True)
class ReadingQuestion:
    """One deterministically scored question with review evidence."""

    question_id: str
    question_type: str
    question: str
    options: tuple[str, ...]
    correct_answer: str
    explanation: str
    evidence: str


@dataclass(frozen=True)
class ReadingPassage:
    """One versioned original passage and its complete question set."""

    passage_id: str
    version: str
    title: str
    sections: tuple[ReadingSection, ...]
    questions: tuple[ReadingQuestion, ...]
    source_type: str
    source_name: str
    copyright_notice: str
    is_official_ielts_content: bool

    @property
    def word_count(self) -> int:
        """Return an English word count for source-quality checks."""

        text = " ".join(section.text for section in self.sections)
        return len(re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", text))


@dataclass(frozen=True)
class ReadingBank:
    """A validated immutable collection of original reading passages."""

    bank_id: str
    version: str
    passages: tuple[ReadingPassage, ...]


def _required_text(payload: dict[str, Any], field: str) -> str:
    """Read one required non-empty string from untrusted JSON."""

    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value.strip()


def _build_question(payload: dict[str, Any]) -> ReadingQuestion:
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
    return ReadingQuestion(
        question_id=_required_text(payload, "question_id"),
        question_type=question_type,
        question=_required_text(payload, "question"),
        options=clean_options,
        correct_answer=correct_answer,
        explanation=_required_text(payload, "explanation"),
        evidence=_required_text(payload, "evidence"),
    )


def _build_passage(
    payload: dict[str, Any],
    *,
    version: str,
    source: dict[str, Any],
) -> ReadingPassage:
    """Validate and construct one passage."""

    raw_sections = payload.get("sections")
    raw_questions = payload.get("questions")
    if not isinstance(raw_sections, list) or len(raw_sections) < 5:
        raise ValueError("invalid_sections")
    if not isinstance(raw_questions, list) or not 8 <= len(raw_questions) <= 10:
        raise ValueError("invalid_question_count")
    sections = tuple(
        ReadingSection(
            label=_required_text(section, "label"),
            text=_required_text(section, "text"),
        )
        for section in raw_sections
        if isinstance(section, dict)
    )
    questions = tuple(
        _build_question(question)
        for question in raw_questions
        if isinstance(question, dict)
    )
    if len(sections) != len(raw_sections) or len(questions) != len(raw_questions):
        raise ValueError("invalid_passage_items")
    passage = ReadingPassage(
        passage_id=_required_text(payload, "passage_id"),
        version=version,
        title=_required_text(payload, "title"),
        sections=sections,
        questions=questions,
        source_type=_required_text(source, "source_type"),
        source_name=_required_text(source, "source_name"),
        copyright_notice=_required_text(source, "copyright_notice"),
        is_official_ielts_content=source.get("is_official_ielts_content") is True,
    )
    if not 800 <= passage.word_count <= 1000:
        raise ValueError("invalid_passage_word_count")
    if {question.question_type for question in questions} != VALID_QUESTION_TYPES:
        raise ValueError("missing_question_type")
    return passage


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
    passages = tuple(
        _build_passage(item, version=version, source=source)
        for item in raw_passages
        if isinstance(item, dict)
    )
    passage_ids = [passage.passage_id for passage in passages]
    question_ids = [
        question.question_id
        for passage in passages
        for question in passage.questions
    ]
    if (
        len(passages) != 3
        or tuple(passage_ids) != READING_PASSAGE_IDS
        or len(set(question_ids)) != len(question_ids)
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


def get_reading_passage(passage_id: str) -> ReadingPassage:
    """Return one passage by stable identifier."""

    for passage in get_reading_bank().passages:
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
