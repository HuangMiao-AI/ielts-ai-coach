"""Tests for reading submission, persistence, isolation, and task sync."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import (
    StudyLog,
    TaskQuestionAttempt,
)
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.reading_practice import (
    ReadingPracticeError,
    get_reading_practice_state,
    list_reading_history,
    submit_reading_practice,
)
from ielts_ai_coach.services.scores import save_score_record
from ielts_ai_coach.services.tasks import (
    TaskUpdateError,
    cancel_task_completion,
)


def _prepare_reader(
    username: str,
    session_factory: sessionmaker[Session],
    today: date,
) -> tuple[int, int]:
    """Create a user whose active plan includes a reading task."""

    user_id = register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname=username,
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=60),
        daily_study_minutes=120,
        today=today,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 5.0,
            "writing": 6.5,
            "speaking": 6.5,
        },
        session_factory=session_factory,
    )
    plan = generate_plan(
        user_id,
        today=today,
        session_factory=session_factory,
    )
    reading_task = next(
        task
        for task in plan.tasks
        if task.subject == "reading" and task.task_date == today
    )
    return user_id, reading_task.id


def _correct_answers(user_id: int, task_id: int, session_factory):
    """Return the complete correct answer mapping for one user-owned task."""

    state = get_reading_practice_state(
        user_id=user_id,
        task_id=task_id,
        session_factory=session_factory,
    )
    assert state is not None
    return {
        question.question_id: question.correct_answer
        for question in state.passage.questions
    }


def test_submission_persists_history_and_completes_task_atomically(
    session_factory: sessionmaker[Session],
) -> None:
    """One valid submission must save review data, completion, and one log."""

    today = date(2026, 7, 16)
    user_id, task_id = _prepare_reader("PracticeOwner", session_factory, today)
    answers = _correct_answers(user_id, task_id, session_factory)

    state = submit_reading_practice(
        user_id=user_id,
        task_id=task_id,
        answers=answers,
        session_factory=session_factory,
    )

    assert state.score is not None
    assert state.score.correct_count == 9
    assert state.task.status == "completed"
    assert state.task.actual_minutes == state.task.planned_minutes
    with session_factory() as session:
        attempt = session.scalar(
            select(TaskQuestionAttempt).where(
                TaskQuestionAttempt.user_id == user_id,
                TaskQuestionAttempt.task_id == task_id,
            )
        )
        logs = list(
            session.scalars(
                select(StudyLog).where(
                    StudyLog.user_id == user_id,
                    StudyLog.task_id == task_id,
                )
            )
        )
    assert attempt is not None
    assert attempt.score == attempt.total_questions == 9
    assert attempt.accuracy == 1.0
    assert len(logs) == 1
    history = list_reading_history(
        user_id,
        session_factory=session_factory,
    )
    assert history[0].task_id == task_id
    assert history[0].incorrect_question_ids == ()


def test_incomplete_duplicate_and_cross_user_submissions_are_rejected(
    session_factory: sessionmaker[Session],
) -> None:
    """Submission requires all answers, ownership, and no prior final attempt."""

    today = date(2026, 7, 16)
    owner_id, task_id = _prepare_reader("ReadingOwner", session_factory, today)
    other_id, _ = _prepare_reader("ReadingOther", session_factory, today)
    answers = _correct_answers(owner_id, task_id, session_factory)

    with pytest.raises(ReadingPracticeError, match="incomplete_answers"):
        submit_reading_practice(
            user_id=owner_id,
            task_id=task_id,
            answers=dict(list(answers.items())[:-1]),
            session_factory=session_factory,
        )
    with pytest.raises(ReadingPracticeError, match="task_not_found"):
        submit_reading_practice(
            user_id=other_id,
            task_id=task_id,
            answers=answers,
            session_factory=session_factory,
        )
    assert (
        get_reading_practice_state(
            user_id=other_id,
            task_id=task_id,
            session_factory=session_factory,
        )
        is None
    )

    submit_reading_practice(
        user_id=owner_id,
        task_id=task_id,
        answers=answers,
        session_factory=session_factory,
    )
    with pytest.raises(ReadingPracticeError, match="already_submitted"):
        submit_reading_practice(
            user_id=owner_id,
            task_id=task_id,
            answers=answers,
            session_factory=session_factory,
        )
    with pytest.raises(TaskUpdateError, match="practice_submission_locked"):
        cancel_task_completion(
            user_id=owner_id,
            task_id=task_id,
            session_factory=session_factory,
        )
    with session_factory() as session:
        attempt_count = int(
            session.scalar(
                select(func.count())
                .select_from(TaskQuestionAttempt)
                .where(TaskQuestionAttempt.task_id == task_id)
            )
            or 0
        )
        log_count = int(
            session.scalar(
                select(func.count())
                .select_from(StudyLog)
                .where(StudyLog.task_id == task_id)
            )
            or 0
        )
    assert attempt_count == 1
    assert log_count == 1
