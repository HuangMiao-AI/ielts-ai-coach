"""Tests that prove user notes are never overwritten or recreated."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.exporting.test_contracts import _record

from ielts_ai_coach.exporting.enums import ExportAction, SourceEntity
from ielts_ai_coach.exporting.errors import (
    ExportConfigurationError,
    ExportWriteError,
)
from ielts_ai_coach.exporting.service import ExportService
import ielts_ai_coach.exporting.service as service_module


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "Miao OS"
    for relative in ("00 Dashboard", "02 IELTS", "99 Templates"):
        (vault / relative).mkdir(parents=True)
    return vault


def test_user_modified_output_is_reported_and_not_overwritten(
    tmp_path: Path,
) -> None:
    vault = _vault(tmp_path)
    service = ExportService(vault_root=vault, state_path=tmp_path / "state.json")
    service.execute([_record()], user_id=1, apply=True)
    note = next((vault / "02 IELTS" / "AI Feedback").rglob("*.md"))
    user_text = note.read_text(encoding="utf-8") + "My personal note\n"
    note.write_text(user_text, encoding="utf-8")

    result = service.execute(
        [_record(overall_summary=("Changed source",))],
        user_id=1,
        apply=True,
    )

    assert [item.action for item in result.items] == [
        ExportAction.CONFLICT_USER_MODIFIED
    ]
    assert note.read_text(encoding="utf-8") == user_text


def test_missing_previous_output_is_not_recreated(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    service = ExportService(vault_root=vault, state_path=tmp_path / "state.json")
    service.execute([_record()], user_id=1, apply=True)
    note = next((vault / "02 IELTS" / "AI Feedback").rglob("*.md"))
    note.unlink()

    result = service.execute([_record()], user_id=1, apply=True)

    assert [item.action for item in result.items] == [
        ExportAction.CONFLICT_OUTPUT_MISSING
    ]
    assert not note.exists()


def test_existing_file_with_different_source_key_is_never_overwritten(
    tmp_path: Path,
) -> None:
    vault = _vault(tmp_path)
    service = ExportService(vault_root=vault, state_path=tmp_path / "state.json")
    expected = service.target_path_for(_record())
    expected.parent.mkdir(parents=True)
    different = _record(
        source_entity=SourceEntity.WRITING_FEEDBACK,
        source_record_id=99,
    )
    expected.write_text(service.render(different), encoding="utf-8")
    original = expected.read_text(encoding="utf-8")

    result = service.execute([_record()], user_id=1, apply=True)

    assert [item.action for item in result.items] == [
        ExportAction.CONFLICT_SOURCE_KEY
    ]
    assert expected.read_text(encoding="utf-8") == original


def test_non_miao_vault_is_rejected(tmp_path: Path) -> None:
    service = ExportService(
        vault_root=tmp_path / "wrong",
        state_path=tmp_path / "state.json",
    )

    with pytest.raises(ExportConfigurationError, match="invalid_miao_vault"):
        service.execute([_record()], user_id=1, apply=False)


def test_atomic_write_failure_does_not_update_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vault = _vault(tmp_path)
    state_path = tmp_path / "state.json"
    service = ExportService(vault_root=vault, state_path=state_path)

    def fail_write(target: Path, content: str) -> None:
        raise ExportWriteError("simulated")

    monkeypatch.setattr(service_module, "atomic_write_text", fail_write)
    result = service.execute([_record()], user_id=1, apply=True)

    assert [item.action for item in result.items] == [
        ExportAction.WRITE_FAILED
    ]
    assert not state_path.exists()
    assert not (vault / "02 IELTS" / "AI Feedback").exists()
