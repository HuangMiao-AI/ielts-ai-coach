"""Tests for create, skip, update, and dry-run behavior."""

from __future__ import annotations

from pathlib import Path

from tests.exporting.test_contracts import _record

from ielts_ai_coach.exporting.enums import ExportAction
from ielts_ai_coach.exporting.service import ExportService


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "Miao OS"
    for relative in ("00 Dashboard", "02 IELTS", "99 Templates"):
        (vault / relative).mkdir(parents=True)
    return vault


def test_first_apply_creates_and_second_apply_skips_without_duplicates(
    tmp_path: Path,
) -> None:
    vault = _vault(tmp_path)
    state_path = tmp_path / "state.json"
    service = ExportService(vault_root=vault, state_path=state_path)

    first = service.execute([_record()], user_id=1, apply=True)
    second = service.execute([_record()], user_id=1, apply=True)
    notes = list((vault / "02 IELTS" / "AI Feedback").rglob("*.md"))

    assert [item.action for item in first.items] == [ExportAction.CREATE]
    assert [item.action for item in second.items] == [
        ExportAction.SKIP_UNCHANGED
    ]
    assert len(notes) == 1
    assert state_path.is_file()


def test_changed_source_safely_updates_unchanged_output(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    service = ExportService(
        vault_root=vault,
        state_path=tmp_path / "state.json",
    )
    service.execute([_record()], user_id=1, apply=True)
    changed = _record(overall_summary=("Score: 9/9",))

    result = service.execute([changed], user_id=1, apply=True)
    note = next((vault / "02 IELTS" / "AI Feedback").rglob("*.md"))

    assert [item.action for item in result.items] == [ExportAction.SAFE_UPDATE]
    assert "Score: 9/9" in note.read_text(encoding="utf-8")


def test_dry_run_writes_neither_vault_nor_state(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    state_path = tmp_path / "state.json"
    service = ExportService(vault_root=vault, state_path=state_path)

    result = service.execute([_record()], user_id=1, apply=False)

    assert [item.action for item in result.items] == [ExportAction.CREATE]
    assert not (vault / "02 IELTS" / "AI Feedback").exists()
    assert not state_path.exists()
