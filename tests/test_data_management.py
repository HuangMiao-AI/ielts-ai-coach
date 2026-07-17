"""Tests for user-owned learning and AI data deletion."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.ai.mock import MockAIProvider
from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import (
    CoachMessage,
    Essay,
    ScoreRecord,
    StudentProfile,
    StudyPlan,
    TaskQuestionAttempt,
    User,
    WritingFeedback,
)
from ielts_ai_coach.services.coaching import send_coach_message
from ielts_ai_coach.services.data_management import (
    clear_ai_content,
    clear_learning_records,
)
from ielts_ai_coach.services.planning import generate_plan
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.reading_practice import (
    get_reading_practice_state,
    submit_reading_practice,
)
from ielts_ai_coach.services.scores import save_score_record
from ielts_ai_coach.services.writing import submit_essay


def _prepare_owned_data(
    username: str,
    session_factory: sessionmaker[Session],
    today: date,
) -> int:
    """Create every deletable data type for one user."""

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
        exam_date=today + timedelta(days=90),
        daily_study_minutes=60,
        today=today,
        session_factory=session_factory,
    )
    save_score_record(
        user_id=user_id,
        scores={
            "listening": 6.5,
            "reading": 6.0,
            "writing": 5.5,
            "speaking": 6.0,
        },
        session_factory=session_factory,
    )
    plan = generate_plan(
        user_id,
        today=today,
        session_factory=session_factory,
    )
    reading_task = next(task for task in plan.tasks if task.subject == "reading")
    reading_state = get_reading_practice_state(
        user_id=user_id,
        task_id=reading_task.id,
        session_factory=session_factory,
    )
    assert reading_state is not None
    submit_reading_practice(
        user_id=user_id,
        task_id=reading_task.id,
        answers={
            question.question_id: question.correct_answer
            for question in reading_state.passage.questions
        },
        session_factory=session_factory,
    )
    send_coach_message(
        user_id=user_id,
        content="请给我今天的建议",
        provider=MockAIProvider(),
        today=today,
        session_factory=session_factory,
    )
    submit_essay(
        user_id=user_id,
        test_type="Academic",
        task_type="Task 2",
        prompt="Discuss practical skills in school.",
        content="Schools should teach useful skills for students and society.",
        provider=MockAIProvider(),
        today=today,
        session_factory=session_factory,
    )
    return user_id


def _count(session: Session, model: type, user_id: int) -> int:
    """Count one user's rows in a business table."""

    return int(
        session.scalar(
            select(func.count()).select_from(model).where(model.user_id == user_id)
        )
        or 0
    )


def test_deletion_removes_only_selected_users_optional_data(
    session_factory: sessionmaker[Session],
) -> None:
    """Deleting one user's data must preserve their account and other users."""

    today = date(2026, 7, 16)
    owner_id = _prepare_owned_data("DeleteOwner", session_factory, today)
    other_id = _prepare_owned_data("DeleteOther", session_factory, today)

    learning_counts = clear_learning_records(
        owner_id, session_factory=session_factory
    )
    ai_counts = clear_ai_content(owner_id, session_factory=session_factory)

    assert learning_counts.scores == 1
    assert learning_counts.plans == 1
    assert learning_counts.attempts == 1
    assert ai_counts.essays == 1
    assert ai_counts.messages == 2
    with session_factory() as session:
        assert session.get(User, owner_id) is not None
        assert _count(session, StudentProfile, owner_id) == 1
        for model in (
            ScoreRecord,
            StudyPlan,
            TaskQuestionAttempt,
            CoachMessage,
            Essay,
            WritingFeedback,
        ):
            assert _count(session, model, owner_id) == 0
            assert _count(session, model, other_id) > 0
