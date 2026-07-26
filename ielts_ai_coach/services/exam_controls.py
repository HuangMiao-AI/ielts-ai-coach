"""Shared immutable controls for timed IELTS practice sessions."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import re


class ExamControlError(ValueError):
    """Raised when an exam control transition is invalid."""


class ExamStatus(str, Enum):
    """Allowed lifecycle states for every skill exam."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    SUBMIT_CONFIRM = "submit_confirm"
    TIMED_OUT = "timed_out"
    SUBMITTED = "submitted"


@dataclass(frozen=True)
class ExamMode:
    """Policy switches for practice and future full mock exams."""

    allow_pause: bool
    allow_manual_submit: bool
    auto_submit_on_timeout: bool


EXAM_MODES = {
    "practice": ExamMode(True, True, False),
    "full_mock": ExamMode(False, True, True),
}


@dataclass(frozen=True)
class ExamSession:
    """Server-owned time and lifecycle state for one skill session."""

    session_id: str
    skill: str
    mode: str
    status: ExamStatus
    started_at: datetime
    deadline: datetime
    paused_at: datetime | None = None
    accumulated_pause_seconds: int = 0
    submitted_at: datetime | None = None
    timed_out: bool = False

    def remaining_seconds(self, *, now: datetime | None = None) -> int:
        """Return a frozen or wall-clock remaining duration, clamped at zero."""

        current = now or datetime.now(timezone.utc)
        end = self.paused_at if self.status is ExamStatus.PAUSED else current
        return max(0, int((self.deadline - end).total_seconds()))


def create_exam_session(*, session_id: str, skill: str, mode: str, duration_seconds: int, now: datetime | None = None) -> ExamSession:
    """Create and start one validated practice or full-mock session."""

    if not session_id.strip() or not skill.strip() or mode not in EXAM_MODES or duration_seconds <= 0:
        raise ExamControlError("invalid_exam_session")
    started = now or datetime.now(timezone.utc)
    return ExamSession(session_id, skill, mode, ExamStatus.RUNNING, started, started + timedelta(seconds=duration_seconds))


def _require(session: ExamSession, status: ExamStatus) -> None:
    """Require one exact lifecycle state."""

    if session.status is not status:
        raise ExamControlError("invalid_transition")

def pause_exam(session: ExamSession, *, now: datetime | None = None) -> ExamSession:
    """Freeze an eligible practice session once."""

    if not EXAM_MODES[session.mode].allow_pause:
        raise ExamControlError("pause_not_allowed")
    _require(session, ExamStatus.RUNNING)
    return replace(session, status=ExamStatus.PAUSED, paused_at=now or datetime.now(timezone.utc))

def resume_exam(session: ExamSession, *, now: datetime | None = None) -> ExamSession:
    """Resume from exactly the paused remaining time."""

    _require(session, ExamStatus.PAUSED)
    current = now or datetime.now(timezone.utc)
    assert session.paused_at is not None
    pause_duration = max(timedelta(), current - session.paused_at)
    pause_seconds = int(pause_duration.total_seconds())
    return replace(
        session,
        status=ExamStatus.RUNNING,
        deadline=session.deadline + pause_duration,
        paused_at=None,
        accumulated_pause_seconds=session.accumulated_pause_seconds + pause_seconds,
    )

def request_submission(session: ExamSession) -> ExamSession:
    """Open a reversible submit confirmation while the timer continues."""

    if not EXAM_MODES[session.mode].allow_manual_submit:
        raise ExamControlError("submit_not_allowed")
    if session.status is ExamStatus.TIMED_OUT and session.mode == "practice":
        return replace(session, status=ExamStatus.SUBMIT_CONFIRM)
    _require(session, ExamStatus.RUNNING)
    return replace(session, status=ExamStatus.SUBMIT_CONFIRM)

def cancel_submission(session: ExamSession) -> ExamSession:
    """Return from confirmation without altering time or content."""

    _require(session, ExamStatus.SUBMIT_CONFIRM)
    status = ExamStatus.TIMED_OUT if session.timed_out else ExamStatus.RUNNING
    return replace(session, status=status)

def mark_submitted(session: ExamSession, *, now: datetime | None = None) -> ExamSession:
    """Lock a confirmed submission exactly once."""

    _require(session, ExamStatus.SUBMIT_CONFIRM)
    return replace(session, status=ExamStatus.SUBMITTED, submitted_at=now or datetime.now(timezone.utc))


def timeout_exam(session: ExamSession, *, now: datetime | None = None) -> ExamSession:
    """Lock an elapsed running session without creating a duplicate result."""

    if session.status not in {
        ExamStatus.RUNNING,
        ExamStatus.SUBMIT_CONFIRM,
    }:
        raise ExamControlError("invalid_transition")
    if session.remaining_seconds(now=now) > 0:
        raise ExamControlError("time_remaining")
    return replace(session, status=ExamStatus.TIMED_OUT, timed_out=True)


def reconcile_exam(
    session: ExamSession,
    *,
    now: datetime | None = None,
) -> ExamSession:
    """Apply a wall-clock timeout to an active session exactly once."""

    if session.status not in {
        ExamStatus.RUNNING,
        ExamStatus.SUBMIT_CONFIRM,
    }:
        return session
    if session.status is ExamStatus.SUBMIT_CONFIRM and session.timed_out:
        return session
    if session.remaining_seconds(now=now) > 0:
        return session
    return timeout_exam(session, now=now)


def serialize_exam_session(
    session: ExamSession,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return primitive Streamlit-session-safe state without user content."""

    return {
        "session_id": session.session_id,
        "skill": session.skill,
        "mode": session.mode,
        "status": session.status.value,
        "started_at": session.started_at.isoformat(),
        "deadline": session.deadline.isoformat(),
        "remaining_seconds": session.remaining_seconds(now=now),
        "paused_at": session.paused_at.isoformat() if session.paused_at else None,
        "accumulated_pause_seconds": session.accumulated_pause_seconds,
        "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
        "timed_out": session.timed_out,
    }


def restore_exam_session(payload: object) -> ExamSession:
    """Restore validated primitive state after a Streamlit rerun."""

    if not isinstance(payload, dict):
        raise ExamControlError("invalid_serialized_session")
    try:
        status = ExamStatus(str(payload["status"]))
        mode = str(payload["mode"])
        if mode not in EXAM_MODES:
            raise ValueError
        paused_at = payload.get("paused_at")
        submitted_at = payload.get("submitted_at")
        return ExamSession(
            session_id=str(payload["session_id"]),
            skill=str(payload["skill"]),
            mode=mode,
            status=status,
            started_at=datetime.fromisoformat(str(payload["started_at"])),
            deadline=datetime.fromisoformat(str(payload["deadline"])),
            paused_at=datetime.fromisoformat(str(paused_at)) if paused_at else None,
            accumulated_pause_seconds=int(payload["accumulated_pause_seconds"]),
            submitted_at=datetime.fromisoformat(str(submitted_at)) if submitted_at else None,
            timed_out=payload["timed_out"] is True,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ExamControlError("invalid_serialized_session") from error


def _key_part(value: str) -> str:
    """Return one bounded state-key segment."""

    normalized = re.sub(
        r"[^a-z0-9-]+",
        "-",
        value.strip().casefold(),
    ).strip("-")
    if not normalized:
        raise ExamControlError("invalid_exam_session")
    return normalized


def exam_control_key(user_id: int, skill: str, task_key: str) -> str:
    """Return one authenticated user, skill, and task state key."""

    if user_id <= 0:
        raise ExamControlError("invalid_exam_session")
    return (
        f"exam_control_{user_id}_{_key_part(skill)}_"
        f"{_key_part(task_key)}"
    )


def load_exam_control(
    store: MutableMapping[str, object],
    *,
    user_id: int,
    skill: str,
    task_key: str,
    duration_seconds: int,
    mode: str = "practice",
    now: datetime | None = None,
) -> ExamSession:
    """Restore one exact serialized controller or start a fresh session."""

    key = exam_control_key(user_id, skill, task_key)
    saved = store.get(key)
    try:
        session = (
            saved
            if isinstance(saved, ExamSession)
            else restore_exam_session(saved)
        )
    except ExamControlError:
        session = None
    if (
        isinstance(session, ExamSession)
        and session.session_id == key
        and session.skill == _key_part(skill)
        and session.mode == mode
    ):
        return session
    created = create_exam_session(
        session_id=key,
        skill=_key_part(skill),
        mode=mode,
        duration_seconds=duration_seconds,
        now=now,
    )
    store[key] = serialize_exam_session(created, now=now)
    return created


def save_exam_control(
    store: MutableMapping[str, object],
    *,
    user_id: int,
    task_key: str,
    session: ExamSession,
    now: datetime | None = None,
) -> None:
    """Save one validated controller as primitive session-safe state."""

    key = exam_control_key(user_id, session.skill, task_key)
    if session.session_id != key:
        raise ExamControlError("invalid_exam_session")
    store[key] = serialize_exam_session(session, now=now)


def clear_exam_control(
    store: MutableMapping[str, object],
    *,
    user_id: int,
    skill: str,
    task_key: str,
) -> None:
    """Remove one transient controller without touching user content."""

    store.pop(exam_control_key(user_id, skill, task_key), None)
