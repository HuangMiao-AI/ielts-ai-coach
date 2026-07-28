"""Contracts for the shared full-page exam hard-pause layer."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_hard_pause_client_locks_root_scroll_focus_and_restores_state() -> None:
    """Paused content must be hidden, inert, non-scrollable, and recoverable."""

    source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "components"
        / "exam_hard_pause"
        / "frontend"
        / "index.html"
    ).read_text(encoding="utf-8")

    assert "inert" in source
    assert "overflow" in source
    assert "wheel" in source
    assert "touchmove" in source
    assert "keydown" in source
    assert "scrollTop" in source
    assert "pagehide" in source
    assert "考试已暂停" in source
    assert "恢复考试" in source


def test_control_panel_keeps_the_client_mount_while_paused() -> None:
    """The hard-pause client must not replace the timer component's iframe."""

    source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "views"
        / "exam_control_panel.py"
    ).read_text(encoding="utf-8")

    assert source.index("_render_live_timer(session") < source.index(
        "if session.status is ExamStatus.PAUSED:"
    )
