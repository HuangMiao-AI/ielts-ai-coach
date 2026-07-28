"""Transient Listening audio controller state contracts."""

from __future__ import annotations

from ielts_ai_coach.services.listening_session import (
    get_listening_audio_command,
    record_listening_audio_state,
    request_listening_audio_command,
)
from ielts_ai_coach.ui.exam_audio import AudioPlaybackState


def test_listening_audio_command_ids_are_monotonic_and_last_state_is_retained() -> None:
    """A browser rerun never reissues a pause or discards its exact position."""

    store: dict[str, object] = {}
    assert get_listening_audio_command(store, 7, "LISTEN-V1-001") == ("load", 0)

    assert request_listening_audio_command(store, 7, "LISTEN-V1-001", "pause") == 1
    assert request_listening_audio_command(store, 7, "LISTEN-V1-001", "resume") == 2
    assert get_listening_audio_command(store, 7, "LISTEN-V1-001") == ("resume", 2)

    state = AudioPlaybackState(
        current_time=31.2,
        duration=320.0,
        playback_state="paused",
        ready=True,
    )
    record_listening_audio_state(store, 7, "LISTEN-V1-001", state)
    assert store["skill_draft_7_listening_listen-v1-001_audio_state"] == {
        "current_time": 31.2,
        "duration": 320.0,
        "playback_state": "paused",
        "ended": False,
        "ready": True,
        "error": None,
    }


def test_blank_component_rerun_does_not_erase_confirmed_audio_position() -> None:
    """A remounted player must resume from its last browser-confirmed position."""

    store: dict[str, object] = {}
    record_listening_audio_state(
        store,
        7,
        "LISTEN-V1-001",
        AudioPlaybackState(
            current_time=36.8,
            duration=131.0,
            playback_state="paused",
            ready=True,
        ),
    )

    record_listening_audio_state(store, 7, "LISTEN-V1-001", AudioPlaybackState())

    assert store["skill_draft_7_listening_listen-v1-001_audio_state"]["current_time"] == 36.8
