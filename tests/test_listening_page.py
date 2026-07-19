"""Contracts for the honest local Listening demo flow."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_listening_page_has_sections_timer_confirmation_and_no_score_claim() -> None:
    """The demo may guide practice but must not imply real scoring."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "listening.py"
    ).read_text(encoding="utf-8")

    assert "Demo" in source
    assert "选择练习" in source
    assert "Section 1" in source and "Section 4" in source
    assert "剩余时间" in source
    assert "确认完成" in source
    assert "不保存分数" in source
    assert "自动评分" not in source
