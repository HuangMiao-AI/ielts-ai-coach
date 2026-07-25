"""Original Writing task bank and non-scoring local structure checks."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

from ielts_ai_coach.services.writing import count_words


BANK_PATH = (
    Path(__file__).resolve().parent.parent
    / "content"
    / "question_banks"
    / "writing_v1.json"
)


@dataclass(frozen=True)
class WritingTask:
    """One project-original IELTS-style prompt."""

    task_id: str
    title: str
    test_type: str
    task_type: str
    suggested_minutes: int
    minimum_words: int
    prompt: str


@dataclass(frozen=True)
class WritingTaskBank:
    """Validated immutable collection of original prompts."""

    bank_id: str
    version: str
    source_type: str
    copyright_notice: str
    is_official_ielts_content: bool
    tasks: tuple[WritingTask, ...]


@dataclass(frozen=True)
class WritingLocalChecks:
    """Basic observations that deliberately contain no IELTS band."""

    word_count: int
    paragraph_count: int
    meets_recommended_length: bool
    has_introduction: bool
    has_conclusion: bool


def _text(payload: dict[str, Any], field: str) -> str:
    """Read one required non-empty string."""

    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value.strip()


@lru_cache(maxsize=1)
def load_writing_tasks(path: Path | None = None) -> WritingTaskBank:
    """Load and validate the project-original Writing task bank."""

    payload = json.loads((path or BANK_PATH).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid_bank")
    source = payload.get("source")
    raw_tasks = payload.get("tasks")
    if (
        not isinstance(source, dict)
        or source.get("source_type") != "project_original"
        or source.get("is_official_ielts_content") is not False
        or not isinstance(raw_tasks, list)
    ):
        raise ValueError("invalid_source")
    tasks = []
    for item in raw_tasks:
        if not isinstance(item, dict):
            raise ValueError("invalid_task")
        test_type = _text(item, "test_type")
        task_type = _text(item, "task_type")
        minutes = item.get("suggested_minutes")
        minimum = item.get("minimum_words")
        if (
            test_type not in {"Academic", "General"}
            or task_type not in {"Task 1", "Task 2"}
            or minutes not in {20, 40}
            or minimum != (150 if task_type == "Task 1" else 250)
        ):
            raise ValueError("invalid_task")
        tasks.append(
            WritingTask(
                task_id=_text(item, "task_id"),
                title=_text(item, "title"),
                test_type=test_type,
                task_type=task_type,
                suggested_minutes=minutes,
                minimum_words=minimum,
                prompt=_text(item, "prompt"),
            )
        )
    if (
        len(tasks) < 4
        or len({task.task_id for task in tasks}) != len(tasks)
        or {(task.test_type, task.task_type) for task in tasks}
        != {
            ("Academic", "Task 1"),
            ("Academic", "Task 2"),
            ("General", "Task 1"),
            ("General", "Task 2"),
        }
    ):
        raise ValueError("invalid_task_coverage")
    return WritingTaskBank(
        bank_id=_text(payload, "bank_id"),
        version=_text(payload, "version"),
        source_type=_text(source, "source_type"),
        copyright_notice=_text(source, "copyright_notice"),
        is_official_ielts_content=False,
        tasks=tuple(tasks),
    )


def get_writing_task(test_type: str, task_type: str) -> WritingTask:
    """Return the original prompt for one selected test/task combination."""

    for task in load_writing_tasks().tasks:
        if task.test_type == test_type and task.task_type == task_type:
            return task
    raise KeyError("writing_task_not_found")


def inspect_writing_locally(
    content: str,
    *,
    minimum_words: int,
) -> WritingLocalChecks:
    """Report simple structure facts without estimating an IELTS score."""

    paragraphs = tuple(
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", content.strip())
        if paragraph.strip()
    )
    first = paragraphs[0].casefold() if paragraphs else ""
    last = paragraphs[-1].casefold() if paragraphs else ""
    introduction_markers = ("introduction", "this essay", "i am writing")
    conclusion_markers = ("in conclusion", "to conclude", "yours ")
    return WritingLocalChecks(
        word_count=count_words(content),
        paragraph_count=len(paragraphs),
        meets_recommended_length=count_words(content) >= minimum_words,
        has_introduction=(
            len(paragraphs) >= 2
            or any(marker in first for marker in introduction_markers)
        ),
        has_conclusion=any(marker in last for marker in conclusion_markers),
    )
