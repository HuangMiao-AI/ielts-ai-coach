"""Tests for versioned per-user export state."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from ielts_ai_coach.exporting.enums import SourceEntity
from ielts_ai_coach.exporting.errors import ExportStateError
from ielts_ai_coach.exporting.state import (
    ExportState,
    ExportStateEntry,
    load_state,
    save_state,
    state_key,
)


def _entry() -> ExportStateEntry:
    return ExportStateEntry(
        source_entity=SourceEntity.TASK_QUESTION_ATTEMPT,
        source_record_id=7,
        source_fingerprint="a" * 64,
        output_relative_path=(
            "02 IELTS/AI Feedback/2026/"
            "2026-07-19--reading--task-question-attempt-7.md"
        ),
        last_exported_file_hash="b" * 64,
        exported_at=datetime(2026, 7, 19, 3, 0, tzinfo=timezone.utc),
    )


def test_state_round_trip_is_stable_and_user_scoped(tmp_path: Path) -> None:
    path = tmp_path / "obsidian-user-3.json"
    entry = _entry()
    state = ExportState(user_id=3).with_entry(entry)

    save_state(path, state)
    first_bytes = path.read_bytes()
    loaded = load_state(path, user_id=3)
    save_state(path, loaded)

    assert path.read_bytes() == first_bytes
    assert loaded.entries[state_key(entry.source_entity, 7)] == entry
    payload = json.loads(first_bytes)
    assert payload["schema_version"] == 1
    assert payload["exporter_version"] == "1.0.0"
    assert payload["source_system"] == "ielts-ai-coach"
    assert payload["user_id"] == 3
    assert "database" not in repr(payload).lower()


def test_missing_state_returns_empty_but_corrupt_state_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing.json"
    assert load_state(path, user_id=4) == ExportState(user_id=4)

    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ExportStateError, match="state_invalid"):
        load_state(path, user_id=4)


def test_state_for_another_user_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    save_state(path, ExportState(user_id=5))

    with pytest.raises(ExportStateError, match="state_user_mismatch"):
        load_state(path, user_id=6)


def test_state_with_output_outside_managed_directory_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "state.json"
    payload = {
        "schema_version": 1,
        "exporter_version": "1.0.0",
        "source_system": "ielts-ai-coach",
        "user_id": 3,
        "entries": {
            "task_question_attempt:7": {
                "source_entity": "task_question_attempt",
                "source_record_id": 7,
                "source_fingerprint": "a" * 64,
                "output_relative_path": "../outside.md",
                "last_exported_file_hash": "b" * 64,
                "exported_at": "2026-07-19T03:00:00Z",
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExportStateError, match="state_invalid"):
        load_state(path, user_id=3)
