"""User-scoped transient state keys for Listening practice."""

from __future__ import annotations

from ielts_ai_coach.services.skill_sessions import draft_key


_AUDIO_COMMANDS = {"load", "play", "pause", "resume", "stop", "seek_to", "set_locked"}


def _base_key(user_id: int, test_id: str) -> str:
    """Return one validated user/test Listening namespace."""

    return draft_key(user_id, "listening", test_id)


def listening_session_key(user_id: int, test_id: str) -> str:
    """Return the navigation/timer key."""

    return f"{_base_key(user_id, test_id)}_session"


def listening_answer_key(user_id: int, test_id: str) -> str:
    """Return the draft-answer key."""

    return f"{_base_key(user_id, test_id)}_answers"


def listening_confirmation_key(user_id: int, test_id: str) -> str:
    """Return the explicit-submit confirmation key."""

    return f"{_base_key(user_id, test_id)}_confirm"


def listening_result_key(user_id: int, test_id: str) -> str:
    """Return the session-only deterministic result key."""

    return f"{_base_key(user_id, test_id)}_result"


def listening_audio_command_key(user_id: int, test_id: str) -> str:
    """Return the latest controller-owned browser command key."""

    return f"{_base_key(user_id, test_id)}_audio_command"


def listening_audio_state_key(user_id: int, test_id: str) -> str:
    """Return the latest primitive browser playback-state key."""

    return f"{_base_key(user_id, test_id)}_audio_state"


def get_listening_audio_command(
    store: dict[str, object],
    user_id: int,
    test_id: str,
) -> tuple[str, int]:
    """Read the latest command without repeating it on component reruns."""

    payload = store.get(listening_audio_command_key(user_id, test_id))
    if not isinstance(payload, dict):
        return "load", 0
    command = payload.get("command")
    command_id = payload.get("id")
    if command not in _AUDIO_COMMANDS or not isinstance(command_id, int):
        return "load", 0
    return command, max(0, command_id)


def request_listening_audio_command(
    store: dict[str, object],
    user_id: int,
    test_id: str,
    command: str,
) -> int:
    """Issue exactly one monotonically increasing command to the player."""

    if command not in _AUDIO_COMMANDS:
        raise ValueError("invalid_audio_command")
    _, previous_id = get_listening_audio_command(store, user_id, test_id)
    command_id = previous_id + 1
    store[listening_audio_command_key(user_id, test_id)] = {
        "command": command,
        "id": command_id,
    }
    return command_id


def record_listening_audio_state(
    store: dict[str, object],
    user_id: int,
    test_id: str,
    state: object,
) -> None:
    """Persist only primitive playback values for a later resume seek."""

    current_time = float(getattr(state, "current_time", 0.0))
    duration = float(getattr(state, "duration", 0.0))
    playback_state = str(getattr(state, "playback_state", "idle"))
    ready = getattr(state, "ready", False) is True
    error = getattr(state, "error", None)
    existing = store.get(listening_audio_state_key(user_id, test_id))
    is_browser_confirmed = (
        ready
        or current_time > 0
        or duration > 0
        or playback_state in {"playing", "paused", "ended", "error"}
        or isinstance(error, str)
    )
    if not is_browser_confirmed and isinstance(existing, dict):
        return
    store[listening_audio_state_key(user_id, test_id)] = {
        "current_time": current_time,
        "duration": duration,
        "playback_state": playback_state,
        "ended": getattr(state, "ended", False) is True,
        "ready": ready,
        "error": error,
    }


def selected_test_key(user_id: int) -> str:
    """Return the selected Listening test key for one user."""

    if user_id <= 0:
        raise ValueError("invalid_user")
    return f"listening_selected_test_{user_id}"
