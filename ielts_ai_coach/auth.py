"""Authentication and Streamlit session management."""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from typing import Any

import streamlit as st
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import get_session_factory
from ielts_ai_coach.database.models import User
from ielts_ai_coach.database.repositories import (
    create_user,
    get_user_by_id,
    get_user_by_normalized_username,
)


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,24}$")
PASSWORD_HASHER = PasswordHasher(type=Type.ID)
SESSION_KEYS = ("authenticated", "user_id", "username")


class AuthenticationError(Exception):
    """Base exception for authentication failures."""


class InvalidUsernameError(AuthenticationError):
    """Raised when a username does not satisfy V1 rules."""


class InvalidPasswordError(AuthenticationError):
    """Raised when a password does not satisfy V1 rules."""


class UsernameAlreadyExistsError(AuthenticationError):
    """Raised when a normalized username is already registered."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when a login attempt cannot be authenticated."""


class InactiveUserError(AuthenticationError):
    """Raised when a disabled account attempts to log in."""


class AuthenticationRequiredError(AuthenticationError):
    """Raised when a protected page is opened without a valid session."""


def normalize_username(username: str) -> str:
    """Validate and normalize a username for case-insensitive lookup."""

    cleaned_username = username.strip()
    if not USERNAME_PATTERN.fullmatch(cleaned_username):
        raise InvalidUsernameError
    return cleaned_username.casefold()


def validate_password(password: str) -> None:
    """Validate the V1 password length without imposing composition rules."""

    if not 10 <= len(password) <= 128:
        raise InvalidPasswordError


def hash_password(password: str) -> str:
    """Return an Argon2id hash for a validated password."""

    validate_password(password)
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a password matches an Argon2 hash."""

    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def _session_state(
    state: MutableMapping[str, Any] | None,
) -> MutableMapping[str, Any]:
    """Return an injected state mapping or the active Streamlit state."""

    return state if state is not None else st.session_state


def _start_session(
    user: User, state: MutableMapping[str, Any] | None = None
) -> None:
    """Store only the minimum account identity in a session."""

    active_state = _session_state(state)
    active_state["authenticated"] = True
    active_state["user_id"] = user.id
    active_state["username"] = user.username


def register_user(
    username: str,
    password: str,
    *,
    state: MutableMapping[str, Any] | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> User:
    """Register a user securely and start an authenticated session."""

    cleaned_username = username.strip()
    normalized_username = normalize_username(cleaned_username)
    password_hash = hash_password(password)
    factory = session_factory or get_session_factory()

    with factory() as session:
        if get_user_by_normalized_username(session, normalized_username):
            raise UsernameAlreadyExistsError
        try:
            user = create_user(
                session,
                username=cleaned_username,
                username_normalized=normalized_username,
                password_hash=password_hash,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise UsernameAlreadyExistsError from error

    _start_session(user, state)
    return user


def login_user(
    username: str,
    password: str,
    *,
    state: MutableMapping[str, Any] | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> User:
    """Authenticate a user and store their identity in the session."""

    try:
        normalized_username = normalize_username(username)
    except InvalidUsernameError as error:
        raise InvalidCredentialsError from error

    factory = session_factory or get_session_factory()
    with factory() as session:
        user = get_user_by_normalized_username(session, normalized_username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError

    _start_session(user, state)
    return user


def get_current_user(
    *,
    state: MutableMapping[str, Any] | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> User | None:
    """Resolve the current active user from a server-side session."""

    active_state = _session_state(state)
    if active_state.get("authenticated") is not True:
        return None

    user_id = active_state.get("user_id")
    if not isinstance(user_id, int):
        logout(state=active_state)
        return None

    factory = session_factory or get_session_factory()
    with factory() as session:
        user = get_user_by_id(session, user_id)
        if user is None or not user.is_active:
            logout(state=active_state)
            return None
        return user


def require_login(
    *,
    state: MutableMapping[str, Any] | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> User:
    """Return the current user or raise when authentication is required."""

    user = get_current_user(state=state, session_factory=session_factory)
    if user is None:
        raise AuthenticationRequiredError
    return user


def logout(*, state: MutableMapping[str, Any] | None = None) -> None:
    """Clear authentication data from one Streamlit session."""

    active_state = _session_state(state)
    for key in SESSION_KEYS:
        active_state.pop(key, None)
