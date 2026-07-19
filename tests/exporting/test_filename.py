"""Tests for stable cross-device output paths."""

from __future__ import annotations

from tests.exporting.test_contracts import _record

from ielts_ai_coach.exporting.enums import SourceEntity
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
