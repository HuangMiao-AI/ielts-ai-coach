"""Database operations for user accounts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ielts_ai_coach.database.models import User


def create_user(
    session: Session,
    *,
    username: str,
    username_normalized: str,
    password_hash: str,
) -> User:
    """Create a user object and add it to the current transaction."""

    user = User(
        username=username,
        username_normalized=username_normalized,
        password_hash=password_hash,
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def get_user_by_id(session: Session, user_id: int) -> User | None:
    """Return an active or inactive user by primary key."""

    return session.get(User, user_id)


def get_user_by_normalized_username(
    session: Session, username_normalized: str
) -> User | None:
    """Return a user by the case-insensitive username key."""

    statement = select(User).where(
        User.username_normalized == username_normalized
    )
    return session.scalar(statement)
