"""Tests for user-scoped exporter source queries."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.ai.schemas import WritingFeedbackSchema
from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.account_repository import upsert_profile
from ielts_ai_coach.database.exercise_repository import (
    create_task_question_attempt,
)
from ielts_ai_coach.database.models import PlanTask, StudyPlan
from ielts_ai_coach.database.writing_repository import (
    create_essay,
    create_writing_feedback,
)
from ielts_ai_coach.exporting.source_repository import (
    list_export_users,
    list_exportable_reading_attempts,
    list_exportable_writing_feedback,
)


def _seed_user(
    username: str,
    session_factory: sessionmaker[Session],
    *,
    attempt_score: int,
) -> tuple[int, int, int]:
    user_id = register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id
    created = datetime(2026, 7, 19, 2, 30, tzinfo=timezone.utc)
    with session_factory() as session:
        upsert_profile(
            session,
            user_id=user_id,
            nickname=username,
            grade="Grade 11",
            target_overall=7.0,
            exam_date=date(2027, 3, 1),
            daily_study_minutes=90,
        )
        plan = StudyPlan(
            user_id=user_id,
            start_date=date(2026, 7, 19),
            end_date=date(2026, 7, 25),
            phase="foundation",
            status="active",
            created_at=created,
        )
        session.add(plan)
        session.flush()
        task = PlanTask(
            user_id=user_id,
            plan_id=plan.id,
            task_date=date(2026, 7, 19),
            subject="reading",
            task_type="practice",
            title="Private title",
            description="Private description",
            planned_minutes=30,
            priority=1,
            status="completed",
            created_at=created,
        )
        session.add(task)
        session.flush()
        details = {
            "passage_id": "passage-1",
            "passage_version": "1.0",
            "passage_title": "Private passage title",
            "correct_count": attempt_score,
            "total_questions": 2,
            "accuracy": attempt_score / 2,
            "results": [
                {
                    "question_id": "q1",
                    "question_type": "Multiple Choice",
                    "question": "Private full question",
                    "options": ["A", "B"],
                    "user_answer": "A",
                    "correct_answer": "B",
                    "is_correct": False,
                    "explanation": "Review the contrast.",
                    "evidence": "The second sentence gives the contrast.",
                },
                {
                    "question_id": "q2",
                    "question_type": "True/False/Not Given",
                    "question": "Another private question",
                    "options": ["True", "False", "Not Given"],
                    "user_answer": "True",
                    "correct_answer": "True",
                    "is_correct": True,
                    "explanation": "The statement is explicit.",
                    "evidence": "The first sentence states it.",
                },
            ],
        }
        attempt = create_task_question_attempt(
            session,
            user_id=user_id,
            task_id=task.id,
            passage_id="passage-1",
            passage_version="1.0",
            answers_json='{"q1":"A","q2":"True"}',
            results_json=json.dumps(details),
            score=attempt_score,
            total_questions=2,
            accuracy=attempt_score / 2,
            incorrect_question_ids_json='["q1"]',
        )
        attempt.submitted_at = created
        essay = create_essay(
            session,
            user_id=user_id,
            test_type="Academic",
            task_type="Task 2",
            prompt="Private full prompt",
            content="Private full essay content",
            word_count=275,
        )
        essay.created_at = created
        feedback = create_writing_feedback(
            session,
            user_id=user_id,
            essay_id=essay.id,
            feedback=WritingFeedbackSchema(
                task_response_or_achievement=6.0,
                coherence_and_cohesion=6.5,
                lexical_resource=6.0,
                grammatical_range_and_accuracy=5.5,
                estimated_overall=6.0,
                strengths=["Clear position"],
                main_issues=["Sentence control"],
                actionable_suggestions=["Use shorter complex sentences"],
                rewrite_example=(
                    "A clearer paragraph with controlled sentence structure."
                ),
                disclaimer="This is an AI estimate, not an official score.",
            ),
            provider="mock",
            model_name="mock-writing-v1",
        )
        feedback.created_at = created
        session.commit()
        return user_id, attempt.id, feedback.id


def test_export_queries_are_user_scoped_and_allowlisted(
    session_factory: sessionmaker[Session],
) -> None:
    first_id, first_attempt, first_feedback = _seed_user(
        "ExportOne", session_factory, attempt_score=1
    )
    second_id, _, _ = _seed_user(
        "ExportTwo", session_factory, attempt_score=2
    )

    with session_factory() as session:
        reading = list_exportable_reading_attempts(
            session, user_id=first_id
        )
        writing = list_exportable_writing_feedback(
            session, user_id=first_id
        )

    assert [item.source_record_id for item in reading] == [first_attempt]
    assert [item.source_record_id for item in writing] == [first_feedback]
    assert "user_id" not in repr(reading)
    assert "Private full question" not in repr(reading)
    assert "user_answer" not in repr(reading)
    assert "Private full essay content" not in repr(writing)
    assert "Private full prompt" not in repr(writing)
    assert second_id != first_id


def test_export_queries_support_after_id_and_limit(
    session_factory: sessionmaker[Session],
) -> None:
    user_id, attempt_id, feedback_id = _seed_user(
        "ExportCursor", session_factory, attempt_score=1
    )

    with session_factory() as session:
        assert list_exportable_reading_attempts(
            session, user_id=user_id, after_id=attempt_id, limit=1
        ) == []
        assert list_exportable_writing_feedback(
            session, user_id=user_id, after_id=feedback_id, limit=1
        ) == []


def test_user_listing_returns_minimum_identification_and_counts(
    session_factory: sessionmaker[Session],
) -> None:
    user_id, _, _ = _seed_user(
        "ExportSummary", session_factory, attempt_score=1
    )

    with session_factory() as session:
        summaries = list_export_users(session)

    summary = next(item for item in summaries if item.user_id == user_id)
    assert summary.account_label == "ExportSummary"
    assert summary.has_profile is True
    assert summary.reading_count == 1
    assert summary.writing_count == 1
    assert summary.recent_activity_at is not None
    assert not hasattr(summary, "password_hash")
    assert not hasattr(summary, "username_normalized")
