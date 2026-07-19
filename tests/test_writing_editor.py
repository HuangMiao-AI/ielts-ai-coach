"""Contracts for the resilient Writing editor."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_writing_editor_uses_live_isolated_drafts_and_submit_guard() -> None:
    """Task drafts, live count, clear confirmation, and submit lock are required."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "writing.py"
    ).read_text(encoding="utf-8")

    assert "st.form(" not in source
    assert "draft_key(" in source
    assert "count_words(content)" in source
    assert "确认清空当前草稿" in source
    assert "claim_submission(" in source
    assert "release_submission(" in source
