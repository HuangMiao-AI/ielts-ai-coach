"""Pure state-machine tests for the Reading exam workspace."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ielts_ai_coach.services.exam_state import (
    ReadingExamError,
    ReadingExamPhase,
    answer_question,
    cancel_submission,
    create_exam_session,
    elapsed_seconds,
    exam_session_key,
    jump_to_question,
    mark_submitted,
    move_question,
    open_review,
    pause_exam_session,
    remaining_seconds,
    request_submission,
    resume_exam_session,
    start_exam,
    timeout_exam_session,
    unanswered_question_ids,
)
from ielts_ai_coach.services.reading_exam import (
    load_exam_session,
    save_exam_session,
)


QUESTION_IDS = ("Q1", "Q2", "Q3")
STARTED_AT = datetime(2026, 7, 19, 8, 0, tzinfo=timezone.utc)


def test_exam_starts_once_and_navigation_stays_inside_question_range() -> None:
    """Start time must be stable and question navigation must be bounded."""

    session = create_exam_session(
        user_id=7,
        task_id=11,
        question_ids=QUESTION_IDS,
        duration_seconds=3600,
    )
    assert session.phase is ReadingExamPhase.INSTRUCTIONS
    assert session.started_at is None

    session = start_exam(session, now=STARTED_AT)
    restarted = start_exam(session, now=STARTED_AT + timedelta(minutes=5))
    assert restarted.started_at == STARTED_AT
    assert restarted.phase is ReadingExamPhase.IN_PROGRESS
    assert move_question(restarted, -1).current_index == 0
    assert move_question(restarted, 99).current_index == 2
    assert jump_to_question(restarted, "Q2").current_index == 1

    with pytest.raises(ReadingExamError, match="unknown_question"):
        jump_to_question(restarted, "Q9")


def test_answers_progress_confirmation_and_submitted_lock() -> None:
    """Every answer is required before confirmation and final state is locked."""

    session = start_exam(
        create_exam_session(
            user_id=7,
            task_id=11,
            question_ids=QUESTION_IDS,
        ),
        now=STARTED_AT,
    )
    session = answer_question(session, "Q1", " A ")
    assert session.answers == {"Q1": "A"}
    assert unanswered_question_ids(session) == ("Q2", "Q3")
    with pytest.raises(ReadingExamError, match="incomplete_answers:2"):
        request_submission(session)

    session = answer_question(session, "Q2", "TRUE")
    session = answer_question(session, "Q3", "Heading iv")
    confirmation = request_submission(session)
    assert confirmation.phase is ReadingExamPhase.SUBMIT_CONFIRMATION
    assert cancel_submission(confirmation).phase is ReadingExamPhase.IN_PROGRESS

    submitted = mark_submitted(request_submission(session))
    assert submitted.phase is ReadingExamPhase.SUBMITTED
    with pytest.raises(ReadingExamError, match="submitted_locked"):
        answer_question(submitted, "Q1", "B")
    assert open_review(submitted).phase is ReadingExamPhase.REVIEW


def test_timer_and_session_keys_are_deterministic_and_user_scoped() -> None:
    """Timer math and Streamlit state keys must not leak between users."""

    session = start_exam(
        create_exam_session(
            user_id=7,
            task_id=11,
            question_ids=QUESTION_IDS,
            duration_seconds=3600,
        ),
        now=STARTED_AT,
    )
    later = STARTED_AT + timedelta(minutes=12, seconds=5)

    assert elapsed_seconds(session, now=later) == 725
    assert remaining_seconds(session, now=later) == 2875
    assert remaining_seconds(
        session,
        now=STARTED_AT + timedelta(hours=2),
    ) == 0
    assert exam_session_key(7, 11) == "reading_exam_7_11"
    assert exam_session_key(8, 11) != exam_session_key(7, 11)


def test_passage_specific_duration_reaches_zero_without_going_negative() -> None:
    """A 24-minute passage must not inherit the old 60-minute duration."""

    session = start_exam(
        create_exam_session(
            user_id=7,
            task_id=11,
            question_ids=QUESTION_IDS,
            duration_seconds=24 * 60,
        ),
        now=STARTED_AT,
    )

    assert remaining_seconds(session, now=STARTED_AT + timedelta(minutes=23)) == 60
    assert remaining_seconds(session, now=STARTED_AT + timedelta(minutes=25)) == 0


def test_session_adapter_recovers_only_the_matching_user_task_draft() -> None:
    """Session drafts must never be reused for another user or task."""

    store: dict[str, object] = {}
    owner = load_exam_session(
        store,
        user_id=7,
        task_id=11,
        question_ids=QUESTION_IDS,
    )
    owner = answer_question(start_exam(owner, now=STARTED_AT), "Q1", "A")
    save_exam_session(store, owner)

    assert load_exam_session(
        store,
        user_id=7,
        task_id=11,
        question_ids=QUESTION_IDS,
    ).answers == {"Q1": "A"}
    assert load_exam_session(
        store,
        user_id=8,
        task_id=11,
        question_ids=QUESTION_IDS,
    ).answers == {}
    assert load_exam_session(
        store,
        user_id=7,
        task_id=12,
        question_ids=QUESTION_IDS,
    ).answers == {}


def test_reading_session_uses_shared_control_for_pause_and_timeout() -> None:
    """Reading answer state must be locked by the shared controller."""

    session = start_exam(
        create_exam_session(
            user_id=7,
            task_id=11,
            question_ids=QUESTION_IDS,
            duration_seconds=60,
        ),
        now=STARTED_AT,
    )

    paused = pause_exam_session(session, now=STARTED_AT + timedelta(seconds=5))
    with pytest.raises(ReadingExamError, match="answers_not_editable"):
        answer_question(paused, "Q1", "A")

    resumed = resume_exam_session(paused)
    assert answer_question(resumed, "Q1", "A").answers == {"Q1": "A"}

    timed_out = timeout_exam_session(resumed)
    with pytest.raises(ReadingExamError, match="answers_not_editable"):
        answer_question(timed_out, "Q2", "B")
    confirmation = request_submission(timed_out, allow_incomplete=True)
    assert confirmation.phase is ReadingExamPhase.SUBMIT_CONFIRMATION
    assert timeout_exam_session(cancel_submission(confirmation)).phase is (
        ReadingExamPhase.TIMED_OUT
    )
