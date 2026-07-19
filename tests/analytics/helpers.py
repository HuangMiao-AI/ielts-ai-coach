"""Fixtures for analytics service behavior tests."""

from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.models import (
    Essay,
    PlanTask,
    StudyLog,
    StudyPlan,
    TaskQuestionAttempt,
    WritingFeedback,
)
from ielts_ai_coach.database.account_repository import (
    create_score_record,
    upsert_profile,
)


def create_user(username: str, session_factory: sessionmaker[Session]) -> int:
    """Create one isolated test user."""

    return register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id


def add_profile(
    session: Session,
    *,
    user_id: int,
    target_overall: float = 7.0,
    daily_study_minutes: int = 60,
) -> None:
    """Add one profile with analytics-relevant settings."""

    upsert_profile(
        session,
        user_id=user_id,
        nickname="Analytics learner",
        grade="高二",
        target_overall=target_overall,
        exam_date=date(2026, 12, 31),
        daily_study_minutes=daily_study_minutes,
    )


def add_score(
    session: Session,
    *,
    user_id: int,
    overall: float,
    listening: float,
    reading: float,
    writing: float,
    speaking: float,
    recorded_at: datetime,
) -> None:
    """Add one score record with a controlled timestamp."""

    create_score_record(
        session,
        user_id=user_id,
        listening=listening,
        reading=reading,
        writing=writing,
        speaking=speaking,
        overall=overall,
        note="",
        recorded_at=recorded_at,
    )


def add_reading_attempt(
    session: Session,
    *,
    user_id: int,
    score: int,
    total_questions: int,
    results_json: str,
    submitted_at: datetime,
) -> None:
    """Add one reading attempt and its required plan-task ownership chain."""

    plan = StudyPlan(
        user_id=user_id,
        start_date=submitted_at.date(),
        end_date=submitted_at.date(),
        phase="practice",
        status="active",
    )
    session.add(plan)
    session.flush()
    task = PlanTask(
        user_id=user_id,
        plan_id=plan.id,
        task_date=submitted_at.date(),
        subject="reading",
        task_type="practice",
        title="Reading practice",
        description="",
        planned_minutes=30,
        priority=1,
    )
    session.add(task)
    session.flush()
    session.add(
        TaskQuestionAttempt(
            user_id=user_id,
            task_id=task.id,
            passage_id="analytics-passage",
            passage_version="v1",
            answers_json="{}",
            results_json=results_json,
            score=score,
            total_questions=total_questions,
            accuracy=score / total_questions,
            incorrect_question_ids_json="[]",
            submitted_at=submitted_at,
        )
    )


def reading_snapshot(question_types: list[tuple[str, bool]]) -> str:
    """Build a valid serialized ReadingScore-compatible snapshot."""

    correct_count = sum(is_correct for _, is_correct in question_types)
    total_questions = len(question_types)
    return json.dumps(
        {
            "passage_id": "analytics-passage",
            "passage_version": "v1",
            "passage_title": "Analytics passage",
            "correct_count": correct_count,
            "total_questions": total_questions,
            "accuracy": correct_count / total_questions,
            "results": [
                {
                    "question_id": f"q-{index}",
                    "question_type": question_type,
                    "question": "Question",
                    "options": ["A", "B"],
                    "user_answer": "A",
                    "correct_answer": "A" if is_correct else "B",
                    "is_correct": is_correct,
                    "explanation": "Explanation",
                    "evidence": "Evidence",
                }
                for index, (question_type, is_correct) in enumerate(
                    question_types, start=1
                )
            ],
        }
    )


def add_study_log(
    session: Session,
    *,
    user_id: int,
    study_date: date,
    minutes: int,
) -> None:
    """Add one study log and its required task ownership chain."""

    plan = StudyPlan(
        user_id=user_id,
        start_date=study_date,
        end_date=study_date,
        phase="practice",
        status="active",
    )
    session.add(plan)
    session.flush()
    task = PlanTask(
        user_id=user_id,
        plan_id=plan.id,
        task_date=study_date,
        subject="reading",
        task_type="practice",
        title="Study log task",
        description="",
        planned_minutes=minutes,
        priority=1,
        status="completed",
        actual_minutes=minutes,
    )
    session.add(task)
    session.flush()
    session.add(
        StudyLog(
            user_id=user_id,
            task_id=task.id,
            study_date=study_date,
            minutes=minutes,
        )
    )


def add_writing_feedback(
    session: Session,
    *,
    user_id: int,
    task_response: float,
    coherence: float,
    vocabulary: float,
    grammar: float,
    created_at: datetime,
) -> None:
    """Add one completed essay and structured feedback record."""

    essay = Essay(
        user_id=user_id,
        test_type="Academic",
        task_type="Task 2",
        prompt="Prompt",
        content="Essay content",
        word_count=250,
        status="completed",
    )
    session.add(essay)
    session.flush()
    session.add(
        WritingFeedback(
            user_id=user_id,
            essay_id=essay.id,
            task_response_or_achievement=task_response,
            coherence_and_cohesion=coherence,
            lexical_resource=vocabulary,
            grammatical_range_and_accuracy=grammar,
            estimated_overall=(task_response + coherence + vocabulary + grammar)
            / 4,
            strengths=[],
            main_issues=[],
            actionable_suggestions=[],
            rewrite_example="",
            disclaimer="",
            provider="mock",
            model_name="mock-v1",
            raw_metadata={},
            created_at=created_at,
        )
    )
