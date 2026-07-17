"""Versioned structured content for deterministic IELTS study tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Protocol


TASK_CONTENT_PREFIX = "task-content-v1:"
VALID_SUBJECTS = {"listening", "reading", "writing", "speaking"}


class TaskLike(Protocol):
    """Minimal task attributes required by the compatibility parser."""

    title: str
    description: str
    subject: str
    task_type: str
    planned_minutes: int


@dataclass(frozen=True)
class TaskContent:
    """Concrete instructions and completion evidence for one study task."""

    task_title: str
    objective: str
    material: str
    instructions: tuple[str, ...]
    completion_criteria: str
    planned_minutes: int
    subject: str
    difficulty: str
    expected_output: str
    template_id: str = ""
    practice_content: str = ""
    questions: tuple[str, ...] = ()
    answer_key: tuple[str, ...] = ()
    explanations: tuple[str, ...] = ()
    writing_test_type: str = ""
    writing_task_type: str = ""
    writing_prompt: str = ""
    reading_passage_id: str = ""
    reading_passage_version: str = ""


def serialize_task_content(content: TaskContent) -> str:
    """Serialize task content into the existing description text column."""

    payload = asdict(content)
    return TASK_CONTENT_PREFIX + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _read_text(payload: dict[str, object], field: str) -> str:
    """Return one required non-empty string from a JSON payload."""

    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return value.strip()


def _read_string_tuple(
    payload: dict[str, object],
    field: str,
    *,
    required: bool = False,
) -> tuple[str, ...]:
    """Return a clean tuple of strings from a JSON list."""

    value = payload.get(field, [])
    if not isinstance(value, list):
        raise ValueError(f"invalid_{field}")
    items = tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )
    if required and not 3 <= len(items) <= 5:
        raise ValueError(f"invalid_{field}")
    return items


def _parse_payload(payload: dict[str, object]) -> TaskContent:
    """Validate a structured task payload before it reaches the UI."""

    subject = _read_text(payload, "subject")
    minutes = payload.get("planned_minutes")
    if subject not in VALID_SUBJECTS:
        raise ValueError("invalid_subject")
    if not isinstance(minutes, int) or not 1 <= minutes <= 480:
        raise ValueError("invalid_planned_minutes")
    return TaskContent(
        task_title=_read_text(payload, "task_title"),
        objective=_read_text(payload, "objective"),
        material=_read_text(payload, "material"),
        instructions=_read_string_tuple(
            payload, "instructions", required=True
        ),
        completion_criteria=_read_text(payload, "completion_criteria"),
        planned_minutes=minutes,
        subject=subject,
        difficulty=_read_text(payload, "difficulty"),
        expected_output=_read_text(payload, "expected_output"),
        template_id=str(payload.get("template_id", "")).strip(),
        practice_content=str(payload.get("practice_content", "")).strip(),
        questions=_read_string_tuple(payload, "questions"),
        answer_key=_read_string_tuple(payload, "answer_key"),
        explanations=_read_string_tuple(payload, "explanations"),
        writing_test_type=str(
            payload.get("writing_test_type", "")
        ).strip(),
        writing_task_type=str(
            payload.get("writing_task_type", "")
        ).strip(),
        writing_prompt=str(payload.get("writing_prompt", "")).strip(),
        reading_passage_id=str(
            payload.get("reading_passage_id", "")
        ).strip(),
        reading_passage_version=str(
            payload.get("reading_passage_version", "")
        ).strip(),
    )


def _legacy_task_content(task: TaskLike) -> TaskContent:
    """Create safe concrete guidance for a task saved by an older version."""

    subject_labels = {
        "listening": "听力",
        "reading": "阅读",
        "writing": "写作",
        "speaking": "口语",
    }
    label = subject_labels.get(task.subject, "雅思")
    old_description = task.description.strip() or "完成一次对应科目训练"
    return TaskContent(
        task_title=task.title,
        objective=f"完成旧计划中的{label}训练，并记录一个需要改进的问题。",
        material=f"旧计划未保存具体材料；请选择你合法拥有的{label}练习材料。",
        instructions=(
            f"选择一份与“{task.title}”相符的练习材料。",
            f"在计划的{task.planned_minutes}分钟内独立完成训练。",
            f"根据答案或评分标准订正，并记录结果。原说明：{old_description}",
        ),
        completion_criteria="完成所选练习、完成订正，并保存一条复盘记录。",
        planned_minutes=task.planned_minutes,
        subject=task.subject,
        difficulty=task.task_type or "旧计划",
        expected_output="练习结果、错题或自评记录。",
        template_id="legacy-task",
    )


def get_task_content(task: TaskLike) -> TaskContent:
    """Parse a new task or adapt an old task without changing stored data."""

    if not task.description.startswith(TASK_CONTENT_PREFIX):
        return _legacy_task_content(task)
    raw_payload = task.description[len(TASK_CONTENT_PREFIX) :]
    try:
        payload = json.loads(raw_payload)
        if not isinstance(payload, dict):
            raise ValueError("invalid_payload")
        content = _parse_payload(payload)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _legacy_task_content(task)
    if (
        content.subject != task.subject
        or content.planned_minutes != task.planned_minutes
    ):
        return _legacy_task_content(task)
    return content


def is_structured_task(task: TaskLike) -> bool:
    """Return whether a task contains a valid current-version payload."""

    return (
        task.description.startswith(TASK_CONTENT_PREFIX)
        and get_task_content(task).template_id != "legacy-task"
    )
