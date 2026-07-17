"""Tests for registration, password hashing, and login behavior."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import (
    InactiveUserError,
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
    login_user,
    logout,
    register_user,
)
from ielts_ai_coach.database.models import User


def test_registration_stores_argon2id_hash(
    session_factory: sessionmaker[Session],
) -> None:
    """Registration must never persist a plaintext password."""

    state: dict[str, object] = {}
    user = register_user(
        "Student_01",
        "secure-pass-01",
        state=state,
        session_factory=session_factory,
    )

    with session_factory() as session:
        stored_user = session.get(User, user.id)

    assert stored_user is not None
    assert stored_user.password_hash != "secure-pass-01"
    assert stored_user.password_hash.startswith("$argon2id$")
    assert state["user_id"] == user.id
    assert state["authenticated"] is True


def test_equal_passwords_receive_different_salts(
    session_factory: sessionmaker[Session],
) -> None:
    """Two users with one password must receive different hashes."""

    first_user = register_user(
        "FirstUser",
        "shared-pass-01",
        state={},
        session_factory=session_factory,
    )
    second_user = register_user(
        "SecondUser",
        "shared-pass-01",
        state={},
        session_factory=session_factory,
    )

    assert first_user.password_hash != second_user.password_hash


def test_username_is_unique_case_insensitively(
    session_factory: sessionmaker[Session],
) -> None:
    """Normalized usernames must prevent case-only duplicates."""

    register_user(
        "StudentName",
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    )

    with pytest.raises(UsernameAlreadyExistsError):
        register_user(
            "studentname",
            "secure-pass-02",
            state={},
            session_factory=session_factory,
        )


def test_login_accepts_username_with_different_case(
    session_factory: sessionmaker[Session],
) -> None:
    """Login must use the normalized username lookup key."""

    register_user(
        "CaseUser",
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    )
    login_state: dict[str, object] = {}

    logged_in_user = login_user(
        "caseuser",
        "secure-pass-01",
        state=login_state,
        session_factory=session_factory,
    )

    assert logged_in_user.username == "CaseUser"
    assert login_state["user_id"] == logged_in_user.id


def test_wrong_password_does_not_create_session(
    session_factory: sessionmaker[Session],
) -> None:
    """A failed login must not authenticate the active session."""

    register_user(
        "LoginUser",
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    )
    login_state: dict[str, object] = {}

    with pytest.raises(InvalidCredentialsError):
        login_user(
            "LoginUser",
            "wrong-password",
            state=login_state,
            session_factory=session_factory,
        )

    assert "authenticated" not in login_state


def test_inactive_user_cannot_log_in(
    session_factory: sessionmaker[Session],
) -> None:
    """An inactive account must be rejected before session creation."""

    user = register_user(
        "InactiveUser",
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    )
    with session_factory() as session:
        stored_user = session.get(User, user.id)
        assert stored_user is not None
        stored_user.is_active = False
        session.commit()

    login_state: dict[str, object] = {}
    with pytest.raises(InactiveUserError):
        login_user(
            "InactiveUser",
            "secure-pass-01",
            state=login_state,
            session_factory=session_factory,
        )

    logout(state=login_state)
    assert login_state == {}
