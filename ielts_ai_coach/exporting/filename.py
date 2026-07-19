"""Stable cross-platform output paths for exported feedback."""

from __future__ import annotations

from pathlib import PurePosixPath

from ielts_ai_coach.exporting.contracts import FeedbackExportRecord
from ielts_ai_coach.exporting.enums import SourceEntity
from ielts_ai_coach.exporting.errors import ExportConfigurationError


ENTITY_FILE_LABELS = {
    SourceEntity.TASK_QUESTION_ATTEMPT: "task-question-attempt",
    SourceEntity.WRITING_FEEDBACK: "writing-feedback",
}
FORBIDDEN_FILENAME_CHARACTERS = frozenset(':\\/?*"<>|')


def _validated_existing_path(value: str) -> PurePosixPath:
    """Accept only a relative Markdown path inside the managed root."""

    path = PurePosixPath(value.replace("\\", "/"))
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.suffix.lower() != ".md"
        or path.parts[:3] != ("02 IELTS", "AI Feedback", path.parts[2])
        or len(path.parts) != 4
    ):
        raise ExportConfigurationError("invalid_state_output_path")
    return path


def output_relative_path(
    record: FeedbackExportRecord,
    *,
    existing_path: str | None = None,
) -> PurePosixPath:
    """Return one deterministic managed path, preserving state history."""

    if existing_path:
        return _validated_existing_path(existing_path)
    entity_label = ENTITY_FILE_LABELS[record.source_entity]
    filename = (
        f"{record.session_date.isoformat()}--{record.skill.value}--"
        f"{entity_label}-{record.source_record_id}.md"
    )
    if FORBIDDEN_FILENAME_CHARACTERS & set(filename):
        raise ExportConfigurationError("unsafe_output_filename")
    return PurePosixPath(
        "02 IELTS",
        "AI Feedback",
        str(record.session_date.year),
        filename,
    )
