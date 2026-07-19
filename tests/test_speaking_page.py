"""Contracts for local-session Speaking practice."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_speaking_page_has_parts_timers_notes_and_local_recording() -> None:
    """Speaking must support practice without claiming recognition or scoring."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "speaking.py"
    ).read_text(encoding="utf-8")

    assert "Part 1" in source and "Part 2" in source and "Part 3" in source
    assert "准备时间" in source and "回答时间" in source
    assert "练习笔记" in source
    assert "st.audio_input" in source
    assert "仅保存在当前会话" in source
    assert "不提供自动评分" in source
