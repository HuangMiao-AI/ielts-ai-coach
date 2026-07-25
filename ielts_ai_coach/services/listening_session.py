"""User-scoped transient state keys for Listening practice."""

from __future__ import annotations

from ielts_ai_coach.services.skill_sessions import draft_key


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
