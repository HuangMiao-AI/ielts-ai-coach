"""Pure transient-state helpers for non-Reading skill practice."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re


@dataclass(frozen=True)
class SkillSession:
    """Stable timer and navigation state for one user-owned skill task."""

    user_id: int
    skill: str
    task_key: str
    item_count: int
    current_index: int
    duration_seconds: int
    started_at: datetime

    @property
    def progress(self) -> float:
        """Return one-based item progress as a zero-to-one ratio."""

        return (self.current_index + 1) / self.item_count


def _key_part(value: str) -> str:
    """Normalize one bounded session-key segment."""

    normalized = re.sub(r"[^a-z0-9-]+", "-", value.strip().casefold()).strip(
        "-"
    )
    if not normalized:
        raise ValueError("invalid_session_key")
    return normalized


def draft_key(user_id: int, skill: str, task_key: str) -> str:
    """Return a transient draft key isolated by user, skill, and task."""

    if user_id <= 0:
        raise ValueError("invalid_user")
    return (
        f"skill_draft_{user_id}_{_key_part(skill)}_{_key_part(task_key)}"
    )


def start_session(
    *,
    session: SkillSession | None = None,
    user_id: int = 0,
    skill: str = "",
    task_key: str = "",
    item_count: int = 1,
    duration_seconds: int = 1,
    now: datetime | None = None,
) -> SkillSession:
    """Create a session once or return its original stable start."""

    if session is not None:
        return session
    if user_id <= 0 or item_count <= 0 or duration_seconds <= 0:
        raise ValueError("invalid_skill_session")
    return SkillSession(
        user_id=user_id,
        skill=_key_part(skill),
        task_key=_key_part(task_key),
        item_count=item_count,
        current_index=0,
        duration_seconds=duration_seconds,
        started_at=now or datetime.now(timezone.utc),
    )


def move_item(session: SkillSession, offset: int) -> SkillSession:
    """Move through practice items while clamping at both ends."""

    index = max(
        0,
        min(session.item_count - 1, session.current_index + offset),
    )
    return replace(session, current_index=index)


def elapsed_seconds(
    session: SkillSession,
    *,
    now: datetime | None = None,
) -> int:
    """Return non-negative whole seconds from the stable start time."""

    current = now or datetime.now(timezone.utc)
    return max(0, int((current - session.started_at).total_seconds()))


def remaining_seconds(
    session: SkillSession,
    *,
    now: datetime | None = None,
) -> int:
    """Return remaining task seconds clamped at zero."""

    return max(
        0,
        session.duration_seconds - elapsed_seconds(session, now=now),
    )


def claim_submission(
    store: MutableMapping[str, object],
    key: str,
) -> bool:
    """Claim an in-flight action once to block duplicate clicks."""

    guard_key = f"submission_guard_{_key_part(key)}"
    if store.get(guard_key) is True:
        return False
    store[guard_key] = True
    return True


def release_submission(
    store: MutableMapping[str, object],
    key: str,
) -> None:
    """Release an in-flight action after success or handled failure."""

    store.pop(f"submission_guard_{_key_part(key)}", None)
