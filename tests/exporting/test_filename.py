"""Tests for stable cross-device output paths."""

from __future__ import annotations

from tests.exporting.test_contracts import _record

import pytest

from ielts_ai_coach.exporting.enums import SourceEntity
from ielts_ai_coach.exporting.errors import ExportConfigurationError
from ielts_ai_coach.exporting.filename import output_relative_path


def test_filename_is_stable_and_cross_platform_safe() -> None:
    record = _record()

    relative = output_relative_path(record)

    assert relative.as_posix() == (
        "02 IELTS/AI Feedback/2026/"
        "2026-07-19--reading--task-question-attempt-7.md"
    )
    assert not set(':\\/?*"<>|') & set(relative.name)


def test_existing_state_path_wins_over_changed_session_date() -> None:
    record = _record(
        source_entity=SourceEntity.WRITING_FEEDBACK,
        source_record_id=42,
    )
    old_path = (
        "02 IELTS/AI Feedback/2025/"
        "2025-12-31--writing--writing-feedback-42.md"
    )

    assert output_relative_path(record, existing_path=old_path).as_posix() == old_path


@pytest.mark.parametrize(
    "unsafe",
    [
        "../outside.md",
        "02 IELTS/Reading/2026/note.md",
        "02 IELTS/AI Feedback/not-a-year/note.md",
        "02 IELTS/AI Feedback/2026/note.txt",
        "02 IELTS/AI Feedback/2026/extra/note.md",
    ],
)
def test_existing_state_path_must_stay_in_managed_directory(
    unsafe: str,
) -> None:
    with pytest.raises(
        ExportConfigurationError, match="invalid_state_output_path"
    ):
        output_relative_path(_record(), existing_path=unsafe)
