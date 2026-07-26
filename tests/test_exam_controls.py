"""Shared exam-control state-machine contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ielts_ai_coach.services.exam_controls import (
    EXAM_MODES,
    ExamControlError,
    ExamStatus,
    exam_control_key,
    create_exam_session,
    cancel_submission,
    load_exam_control,
    mark_submitted,
    pause_exam,
    reconcile_exam,
    request_submission,
    resume_exam,
    restore_exam_session,
    save_exam_control,
    serialize_exam_session,
    timeout_exam,
)


NOW = datetime(2026, 7, 26, 8, 0, tzinfo=timezone.utc)


def test_practice_session_pauses_and_resumes_without_losing_time() -> None:
    """Practice mode freezes the deadline and permits one resume."""

    session = create_exam_session(
        session_id="reading-1",
        skill="reading",
        mode="practice",
        duration_seconds=60,
        now=NOW,
    )
    paused = pause_exam(session, now=NOW + timedelta(seconds=15))
    resumed = resume_exam(paused, now=NOW + timedelta(seconds=45))

    assert EXAM_MODES["practice"].allow_pause is True
    assert paused.status is ExamStatus.PAUSED
    assert paused.remaining_seconds(now=NOW + timedelta(minutes=3)) == 45
    assert resumed.status is ExamStatus.RUNNING
    assert resumed.remaining_seconds(now=NOW + timedelta(seconds=45)) == 45


def test_full_mock_rejects_pause_and_submits_once_after_confirmation() -> None:
    """Full mock mode forbids pausing and its submission transition is strict."""

    session = create_exam_session(
        session_id="listening-1",
        skill="listening",
        mode="full_mock",
        duration_seconds=60,
        now=NOW,
    )
    with pytest.raises(ExamControlError, match="pause_not_allowed"):
        pause_exam(session, now=NOW)

    confirmed = request_submission(session)
    submitted = mark_submitted(confirmed, now=NOW + timedelta(seconds=3))
    assert submitted.status is ExamStatus.SUBMITTED
    with pytest.raises(ExamControlError, match="invalid_transition"):
        mark_submitted(submitted, now=NOW)


def test_timeout_is_terminal_and_never_reports_negative_time() -> None:
    """Timeout locks a session exactly once for either configured mode."""

    session = create_exam_session(
        session_id="writing-1",
        skill="writing",
        mode="practice",
        duration_seconds=10,
        now=NOW,
    )
    timed_out = timeout_exam(session, now=NOW + timedelta(seconds=11))

    assert timed_out.status is ExamStatus.TIMED_OUT
    assert timed_out.timed_out is True
    assert timed_out.remaining_seconds(now=NOW + timedelta(hours=1)) == 0


def test_multiple_pause_cycles_adjust_the_deadline_once_per_real_pause() -> None:
    """Repeated pause/resume cycles preserve exactly their frozen durations."""

    session = create_exam_session(session_id="r", skill="reading", mode="practice", duration_seconds=100, now=NOW)
    first = resume_exam(pause_exam(session, now=NOW + timedelta(seconds=10)), now=NOW + timedelta(seconds=30))
    second = resume_exam(pause_exam(first, now=NOW + timedelta(seconds=40)), now=NOW + timedelta(seconds=70))

    assert second.accumulated_pause_seconds == 50
    assert second.remaining_seconds(now=NOW + timedelta(seconds=70)) == 80
    with pytest.raises(ExamControlError, match="invalid_transition"):
        pause_exam(pause_exam(session, now=NOW), now=NOW)
    with pytest.raises(ExamControlError, match="invalid_transition"):
        resume_exam(second, now=NOW)


def test_resume_preserves_fractional_pause_time_in_the_deadline() -> None:
    """Subsecond rerun timing must not shorten the available exam time."""

    session = create_exam_session(
        session_id="r",
        skill="reading",
        mode="practice",
        duration_seconds=60,
        now=NOW,
    )
    paused = pause_exam(
        session,
        now=NOW + timedelta(seconds=10.25),
    )
    resumed = resume_exam(
        paused,
        now=NOW + timedelta(seconds=11.75),
    )

    assert resumed.deadline == session.deadline + timedelta(seconds=1.5)


def test_confirmation_keeps_running_time_and_cancel_does_not_extend_deadline() -> None:
    """Opening or cancelling confirmation is not a pause mechanism."""

    session = create_exam_session(session_id="r", skill="reading", mode="practice", duration_seconds=60, now=NOW)
    confirm = request_submission(session)
    restored = cancel_submission(confirm)

    assert confirm.remaining_seconds(now=NOW + timedelta(seconds=20)) == 40
    assert restored.remaining_seconds(now=NOW + timedelta(seconds=20)) == 40


def test_timeout_allows_practice_confirmation_but_rejects_resume_and_submission_is_once() -> None:
    """Timed-out practice is locked but can still be explicitly handed in."""

    session = create_exam_session(session_id="r", skill="reading", mode="practice", duration_seconds=1, now=NOW)
    timed_out = timeout_exam(session, now=NOW + timedelta(seconds=2))
    confirmation = request_submission(timed_out)
    submitted = mark_submitted(confirmation, now=NOW + timedelta(seconds=3))

    with pytest.raises(ExamControlError, match="invalid_transition"):
        resume_exam(timed_out, now=NOW)
    with pytest.raises(ExamControlError, match="invalid_transition"):
        request_submission(submitted)
    assert submitted.submitted_at == NOW + timedelta(seconds=3)


def test_serialization_restores_running_wall_clock_and_paused_freeze() -> None:
    """Streamlit reruns recover both wall-clock and frozen session semantics."""

    running = create_exam_session(session_id="w", skill="writing", mode="practice", duration_seconds=60, now=NOW)
    restored_running = restore_exam_session(serialize_exam_session(running, now=NOW + timedelta(seconds=10)))
    paused = pause_exam(running, now=NOW + timedelta(seconds=10))
    restored_paused = restore_exam_session(serialize_exam_session(paused, now=NOW + timedelta(seconds=50)))

    assert restored_running.remaining_seconds(now=NOW + timedelta(seconds=20)) == 40
    assert restored_paused.remaining_seconds(now=NOW + timedelta(hours=1)) == 50
    payload = serialize_exam_session(paused, now=NOW)
    assert {"mode", "status", "started_at", "deadline", "remaining_seconds", "paused_at", "accumulated_pause_seconds", "submitted_at", "timed_out"} <= payload.keys()


def test_confirmation_timeout_and_cancel_preserve_the_locked_timeout() -> None:
    """An expired confirmation must never reopen an editable running session."""

    running = create_exam_session(
        session_id="reading-7-11",
        skill="reading",
        mode="practice",
        duration_seconds=10,
        now=NOW,
    )
    expired = reconcile_exam(
        request_submission(running),
        now=NOW + timedelta(seconds=11),
    )
    confirmation = request_submission(expired)

    assert expired.status is ExamStatus.TIMED_OUT
    assert expired.remaining_seconds(now=NOW + timedelta(hours=1)) == 0
    assert reconcile_exam(
        confirmation,
        now=NOW + timedelta(hours=1),
    ).status is ExamStatus.SUBMIT_CONFIRM
    assert cancel_submission(confirmation).status is ExamStatus.TIMED_OUT


def test_control_store_round_trips_serialized_user_scoped_sessions() -> None:
    """Streamlit state restores one exact user, skill, and task controller."""

    store: dict[str, object] = {}
    created = load_exam_control(
        store,
        user_id=7,
        skill="writing",
        task_key="Academic-Task-2",
        duration_seconds=60,
        now=NOW,
    )
    paused = pause_exam(created, now=NOW + timedelta(seconds=10))
    save_exam_control(store, user_id=7, task_key="Academic-Task-2", session=paused)

    restored = load_exam_control(
        store,
        user_id=7,
        skill="writing",
        task_key="Academic-Task-2",
        duration_seconds=60,
        now=NOW + timedelta(minutes=5),
    )
    other_user = load_exam_control(
        store,
        user_id=8,
        skill="writing",
        task_key="Academic-Task-2",
        duration_seconds=60,
        now=NOW,
    )

    assert exam_control_key(7, "writing", "Academic-Task-2") in store
    assert restored.status is ExamStatus.PAUSED
    assert restored.remaining_seconds(now=NOW + timedelta(hours=1)) == 50
    assert other_user.session_id != restored.session_id
