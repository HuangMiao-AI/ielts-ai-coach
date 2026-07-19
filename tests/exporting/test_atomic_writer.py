"""Tests for same-directory atomic UTF-8 writes."""

from __future__ import annotations

from pathlib import Path

import pytest

from ielts_ai_coach.exporting import atomic_writer
from ielts_ai_coach.exporting.errors import ExportWriteError


def test_atomic_writer_creates_utf8_file_and_removes_temp(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "反馈.md"

    atomic_writer.atomic_write_text(target, "中文 feedback\n")

    assert target.read_text(encoding="utf-8") == "中文 feedback\n"
    assert list(target.parent.glob("*.tmp")) == []


def test_replace_failure_preserves_existing_file_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "feedback.md"
    target.write_text("user version", encoding="utf-8")

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("simulated")

    monkeypatch.setattr(atomic_writer.os, "replace", fail_replace)

    with pytest.raises(ExportWriteError, match="atomic_write_failed"):
        atomic_writer.atomic_write_text(target, "generated version")

    assert target.read_text(encoding="utf-8") == "user version"
    assert list(tmp_path.glob("*.tmp")) == []
