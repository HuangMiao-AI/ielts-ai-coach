"""A packaged Components-v1 wrapper for controller-owned exam audio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


_FRONTEND_PATH = (
    Path(__file__).resolve().parents[1]
    / "components"
    / "exam_audio"
    / "frontend"
)
_exam_audio = components.declare_component(
    "ielts_exam_audio",
    path=str(_FRONTEND_PATH),
)
_PLAYBACK_STATES = {"idle", "loading", "playing", "paused", "ended", "error"}
_COMMANDS = {"load", "play", "pause", "resume", "stop", "seek_to", "set_locked"}


@dataclass(frozen=True)
class AudioPlaybackState:
    """Primitive event data returned by the browser-owned audio element."""

    current_time: float = 0.0
    duration: float = 0.0
    playback_state: str = "idle"
    ended: bool = False
    ready: bool = False
    error: str | None = None


def coerce_audio_state(value: object) -> AudioPlaybackState:
    """Accept only finite, non-negative component event values."""

    if not isinstance(value, dict):
        return AudioPlaybackState()
    state = str(value.get("playback_state", "idle"))
    if state not in _PLAYBACK_STATES:
        state = "idle"
    return AudioPlaybackState(
        current_time=_non_negative_float(value.get("current_time")),
        duration=_non_negative_float(value.get("duration")),
        playback_state=state,
        ended=value.get("ended") is True,
        ready=value.get("ready") is True,
        error=_clean_error(value.get("error")),
    )


def render_exam_audio(
    *,
    audio_url: str,
    command: str,
    command_id: int,
    locked: bool,
    key: str,
    seek_seconds: float | None = None,
) -> AudioPlaybackState:
    """Render the only Listening player and return its latest browser state."""

    if command not in _COMMANDS:
        raise ValueError("invalid_audio_command")
    value = _exam_audio(
        audio_url=audio_url,
        command=command,
        command_id=command_id,
        locked=locked,
        seek_seconds=seek_seconds,
        key=key,
        default=None,
    )
    return coerce_audio_state(value)


def static_audio_url(audio_path: str) -> str:
    """Map a bundled static asset to Streamlit's own static-serving route."""

    normalized = audio_path.replace("\\", "/").lstrip("/")
    if not normalized.startswith("static/audio/"):
        raise ValueError("invalid_audio_path")
    return f"/app/{normalized}"


def _non_negative_float(value: Any) -> float:
    """Normalize browser numeric values without leaking NaN or infinities."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number >= 0 and number < float("inf") else 0.0


def _clean_error(value: object) -> str | None:
    """Keep a short user-displayable component error only."""

    if not isinstance(value, str):
        return None
    cleaned = value.strip()[:160]
    return cleaned or None
