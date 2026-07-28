"""Contracts for the locally packaged, controller-owned Listening audio."""

from __future__ import annotations

from pathlib import Path

from ielts_ai_coach.ui.exam_audio import AudioPlaybackState, coerce_audio_state


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_audio_component_coerces_only_safe_playback_state() -> None:
    """Browser events remain primitive and cannot invent a playing state."""

    state = coerce_audio_state(
        {
            "current_time": "12.5",
            "duration": 42,
            "playback_state": "paused",
            "ended": False,
            "ready": True,
            "error": "",
        }
    )

    assert state == AudioPlaybackState(
        current_time=12.5,
        duration=42.0,
        playback_state="paused",
        ended=False,
        ready=True,
        error=None,
    )
    assert coerce_audio_state({"playback_state": "unknown"}).playback_state == "idle"


def test_packaged_audio_frontend_has_all_controller_commands_and_events() -> None:
    """The component has no Streamlit DOM-selector playback escape hatch."""

    source = (
        PROJECT_ROOT
        / "ielts_ai_coach"
        / "components"
        / "exam_audio"
        / "frontend"
        / "index.html"
    ).read_text(encoding="utf-8")

    for command in ("load", "play", "pause", "resume", "stop", "seek_to", "set_locked"):
        assert f'"{command}"' in source
    for event in ("current_time", "duration", "playback_state", "ended", "ready", "error"):
        assert event in source
    assert "streamlit:componentReady" in source
    assert "st.audio" not in source
    assert "pendingSeek" in source
    assert "args.seek_seconds" in source


def test_listening_page_uses_formal_start_and_hard_pause_without_st_audio() -> None:
    """The official timer/audio must start only after the formal confirmation."""

    source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "listening.py"
    ).read_text(encoding="utf-8")

    assert "render_hard_pause_overlay" in source
    assert "render_controlled_listening_audio" in source
    start_source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "listening_start.py"
    ).read_text(encoding="utf-8")
    assert "开始正式练习" in start_source
    assert "声音测试" in start_source
    audio_source = (
        PROJECT_ROOT / "ielts_ai_coach" / "views" / "listening_audio.py"
    ).read_text(encoding="utf-8")
    assert "render_exam_audio" in audio_source
    assert "st.audio" not in source
