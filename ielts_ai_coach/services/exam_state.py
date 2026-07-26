"""Pure immutable state transitions for the Reading exam workspace."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class ReadingExamError(ValueError):
    """Raised when an exam state transition is invalid."""


class ReadingExamPhase(str, Enum):
    """Supported stages of one Reading exam session."""

    INSTRUCTIONS = "instructions"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    TIMED_OUT = "timed_out"
    SUBMIT_CONFIRMATION = "submit_confirmation"
    SUBMITTED = "submitted"
    REVIEW = "review"


@dataclass(frozen=True)
class ReadingExamSession:
    """Immutable user/task-scoped Reading interaction state."""

    user_id: int
    task_id: int
    question_ids: tuple[str, ...]
    phase: ReadingExamPhase
    current_index: int
    answers: Mapping[str, str]
    duration_seconds: int
    started_at: datetime | None

    @property
    def current_question_id(self) -> str:
        """Return the selected stable question identifier."""

        return self.question_ids[self.current_index]


def _frozen_answers(answers: Mapping[str, str]) -> Mapping[str, str]:
    """Copy answers into a read-only mapping."""

    return MappingProxyType(dict(answers))


def create_exam_session(
    *,
    user_id: int,
    task_id: int,
    question_ids: tuple[str, ...],
    duration_seconds: int = 3600,
) -> ReadingExamSession:
    """Create one validated session at its instruction stage."""

    if (
        user_id <= 0
        or task_id <= 0
        or not question_ids
        or len(question_ids) != len(set(question_ids))
        or any(not question_id.strip() for question_id in question_ids)
        or duration_seconds <= 0
    ):
        raise ReadingExamError("invalid_exam_session")
    return ReadingExamSession(
        user_id=user_id,
        task_id=task_id,
        question_ids=question_ids,
        phase=ReadingExamPhase.INSTRUCTIONS,
        current_index=0,
        answers=_frozen_answers({}),
        duration_seconds=duration_seconds,
        started_at=None,
    )


def start_exam(
    session: ReadingExamSession,
    *,
    now: datetime | None = None,
) -> ReadingExamSession:
    """Start once while preserving the original timer on repeated calls."""

    if session.phase is ReadingExamPhase.IN_PROGRESS:
        return session
    if session.phase is not ReadingExamPhase.INSTRUCTIONS:
        raise ReadingExamError("exam_cannot_start")
    return replace(
        session,
        phase=ReadingExamPhase.IN_PROGRESS,
        started_at=now or datetime.now(timezone.utc),
    )


def answer_question(
    session: ReadingExamSession,
    question_id: str,
    answer: str,
) -> ReadingExamSession:
    """Save one non-empty answer while the exam is editable."""

    if session.phase is not ReadingExamPhase.IN_PROGRESS:
        if session.phase in {
            ReadingExamPhase.SUBMITTED,
            ReadingExamPhase.REVIEW,
        }:
            raise ReadingExamError("submitted_locked")
        raise ReadingExamError("answers_not_editable")
    if question_id not in session.question_ids:
        raise ReadingExamError("unknown_question")
    normalized = answer.strip()
    if not normalized:
        raise ReadingExamError("empty_answer")
    answers = dict(session.answers)
    answers[question_id] = normalized
    return replace(session, answers=_frozen_answers(answers))


def pause_exam_session(
    session: ReadingExamSession,
    *,
    now: datetime | None = None,
) -> ReadingExamSession:
    """Freeze Reading edits; shared controls own the timed UI integration."""

    del now
    if session.phase is not ReadingExamPhase.IN_PROGRESS:
        raise ReadingExamError("exam_cannot_pause")
    return replace(session, phase=ReadingExamPhase.PAUSED)


def resume_exam_session(session: ReadingExamSession) -> ReadingExamSession:
    """Restore Reading edits after the shared controller resumes."""

    if session.phase is not ReadingExamPhase.PAUSED:
        raise ReadingExamError("exam_cannot_resume")
    return replace(session, phase=ReadingExamPhase.IN_PROGRESS)


def timeout_exam_session(session: ReadingExamSession) -> ReadingExamSession:
    """Lock Reading edits after the shared controller reaches zero."""

    if session.phase is not ReadingExamPhase.IN_PROGRESS:
        raise ReadingExamError("exam_cannot_timeout")
    return replace(session, phase=ReadingExamPhase.TIMED_OUT)


def jump_to_question(
    session: ReadingExamSession,
    question_id: str,
) -> ReadingExamSession:
    """Select one question by stable identifier."""

    try:
        index = session.question_ids.index(question_id)
    except ValueError as error:
        raise ReadingExamError("unknown_question") from error
    return replace(session, current_index=index)


def move_question(
    session: ReadingExamSession,
    offset: int,
) -> ReadingExamSession:
    """Move by an offset while clamping to the available range."""

    index = max(
        0,
        min(len(session.question_ids) - 1, session.current_index + offset),
    )
    return replace(session, current_index=index)


def unanswered_question_ids(
    session: ReadingExamSession,
) -> tuple[str, ...]:
    """Return question identifiers with no saved answer."""

    return tuple(
        question_id
        for question_id in session.question_ids
        if not session.answers.get(question_id, "").strip()
    )


def request_submission(
    session: ReadingExamSession,
    *,
    allow_incomplete: bool = False,
) -> ReadingExamSession:
    """Enter confirmation only when every question is answered."""

    if session.phase not in {
        ReadingExamPhase.IN_PROGRESS,
        ReadingExamPhase.TIMED_OUT,
    }:
        raise ReadingExamError("submission_not_available")
    missing = unanswered_question_ids(session)
    if missing and not (
        allow_incomplete
        and session.phase is ReadingExamPhase.TIMED_OUT
    ):
        raise ReadingExamError(f"incomplete_answers:{len(missing)}")
    return replace(
        session,
        phase=ReadingExamPhase.SUBMIT_CONFIRMATION,
    )


def cancel_submission(session: ReadingExamSession) -> ReadingExamSession:
    """Return from confirmation without changing answers or timer."""

    if session.phase is not ReadingExamPhase.SUBMIT_CONFIRMATION:
        raise ReadingExamError("confirmation_not_open")
    return replace(session, phase=ReadingExamPhase.IN_PROGRESS)


def mark_submitted(session: ReadingExamSession) -> ReadingExamSession:
    """Lock a confirmed session after durable submission succeeds."""

    if session.phase is not ReadingExamPhase.SUBMIT_CONFIRMATION:
        raise ReadingExamError("submission_not_confirmed")
    return replace(session, phase=ReadingExamPhase.SUBMITTED)


def open_review(session: ReadingExamSession) -> ReadingExamSession:
    """Open review from a submitted or already reviewed session."""

    if session.phase not in {
        ReadingExamPhase.SUBMITTED,
        ReadingExamPhase.REVIEW,
    }:
        raise ReadingExamError("review_not_available")
    return replace(session, phase=ReadingExamPhase.REVIEW)


def elapsed_seconds(
    session: ReadingExamSession,
    *,
    now: datetime | None = None,
) -> int:
    """Return non-negative whole seconds since the stable start time."""

    if session.started_at is None:
        return 0
    current = now or datetime.now(timezone.utc)
    return max(0, int((current - session.started_at).total_seconds()))


def remaining_seconds(
    session: ReadingExamSession,
    *,
    now: datetime | None = None,
) -> int:
    """Return remaining exam seconds clamped at zero."""

    return max(
        0,
        session.duration_seconds - elapsed_seconds(session, now=now),
    )


def exam_session_key(user_id: int, task_id: int) -> str:
    """Return a Streamlit key isolated by authenticated user and task."""

    return f"reading_exam_{user_id}_{task_id}"
