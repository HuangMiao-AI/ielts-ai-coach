"""Stable cross-platform output paths for exported feedback."""

from __future__ import annotations

from pathlib import PurePosixPath
import re

from ielts_ai_coach.exporting.contracts import FeedbackExportRecord
from ielts_ai_coach.exporting.enums import SourceEntity
from ielts_ai_coach.exporting.errors import ExportConfigurationError


ENTITY_FILE_LABELS = {
    SourceEntity.TASK_QUESTION_ATTEMPT: "task-question-attempt",
    SourceEntity.WRITING_FEEDBACK: "writing-feedback",
}
FORBIDDEN_FILENAME_CHARACTERS = frozenset(':\\/?*"<>|')
_YEAR_DIRECTORY = re.compile(r"^[0-9]{4}$")


def validate_existing_output_path(value: str) -> PurePosixPath:
    """Accept only a relative Markdown path inside the managed root."""

    path = PurePosixPath(value.replace("\\", "/"))
    if (
        path.is_absolute()
        or ".." in path.parts
        or path.suffix.lower() != ".md"
        or len(path.parts) != 4
        or path.parts[:2] != ("02 IELTS", "AI Feedback")
        or not _YEAR_DIRECTORY.fullmatch(path.parts[2])
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
        return validate_existing_output_path(existing_path)
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
