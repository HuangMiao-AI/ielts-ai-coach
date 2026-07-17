"""Tests for per-session user identity isolation."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import (
    AuthenticationRequiredError,
    get_current_user,
    logout,
    register_user,
    require_login,
)


def test_independent_sessions_resolve_independent_users(
    session_factory: sessionmaker[Session],
) -> None:
    """Two session mappings must never share authentication identity."""

    first_state: dict[str, object] = {}
    second_state: dict[str, object] = {}
    first_user = register_user(
        "FirstStudent",
        "secure-pass-01",
        state=first_state,
        session_factory=session_factory,
    )
    second_user = register_user(
        "SecondStudent",
        "secure-pass-02",
        state=second_state,
        session_factory=session_factory,
    )

    assert require_login(
        state=first_state, session_factory=session_factory
    ).id == first_user.id
    assert require_login(
        state=second_state, session_factory=session_factory
    ).id == second_user.id

    logout(state=first_state)

    with pytest.raises(AuthenticationRequiredError):
        require_login(state=first_state, session_factory=session_factory)
    assert get_current_user(
        state=second_state, session_factory=session_factory
    ).id == second_user.id


def test_tampered_session_is_cleared(
    session_factory: sessionmaker[Session],
) -> None:
    """An unknown user ID must invalidate the entire auth session."""

    state: dict[str, object] = {
        "authenticated": True,
        "user_id": 999999,
        "username": "Unknown",
    }

    assert (
        get_current_user(state=state, session_factory=session_factory) is None
    )
    assert state == {}
