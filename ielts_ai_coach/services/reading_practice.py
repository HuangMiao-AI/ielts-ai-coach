"""Reading-practice orchestration, ownership checks, and durable history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Mapping

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.exercise_repository import (
    create_task_question_attempt,
    get_task_question_attempt,
    list_task_question_attempts,
)
from ielts_ai_coach.database.models import PlanTask, TaskQuestionAttempt
from ielts_ai_coach.database.plan_repository import get_task, set_task_completed
from ielts_ai_coach.services.question_bank import (
    ReadingPassage,
    select_reading_passage,
)
from ielts_ai_coach.services.reading_scoring import (
    ReadingScore,
    deserialize_reading_score,
    normalize_answer,
    score_reading_answers,
    serialize_reading_score,
)
from ielts_ai_coach.services.task_content import get_task_content


class ReadingPracticeError(ValueError):
    """Raised for invalid, duplicate, or unauthorized practice submissions."""


@dataclass(frozen=True)
class ReadingPracticeState:
    """One user-owned task's passage and optional submitted result."""

    task: PlanTask
    passage: ReadingPassage
    attempt: TaskQuestionAttempt | None
    score: ReadingScore | None


@dataclass(frozen=True)
class ReadingHistoryItem:
    """Compact persisted reading result for history and future coach context."""

    attempt_id: int
    task_id: int
    passage_title: str
    score: int
    total_questions: int
    accuracy: float
    incorrect_question_ids: tuple[str, ...]
    submitted_at: datetime


def resolve_reading_passage(task: PlanTask) -> ReadingPassage | None:
    """Resolve a stable original passage for an eligible structured task."""

    if task.subject != "reading":
        return None
    content = get_task_content(task)
    if content.template_id == "legacy-task":
        return None
    try:
        passage = select_reading_passage(
            preferred_id=content.reading_passage_id,
            task_id=task.id,
        )
    except KeyError:
        return None
    if (
        content.reading_passage_version
        and content.reading_passage_version != passage.version
    ):
        return None
    return passage


def get_reading_practice_state(
    *,
    user_id: int,
    task_id: int,
    session_factory: sessionmaker[Session] | None = None,
) -> ReadingPracticeState | None:
    """Load a practice only when its task belongs to the current user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        task = get_task(session, user_id=user_id, task_id=task_id)
        if task is None:
            return None
        passage = resolve_reading_passage(task)
        if passage is None:
            return None
        attempt = get_task_question_attempt(
            session,
            user_id=user_id,
            task_id=task_id,
        )
        score = (
            deserialize_reading_score(attempt.results_json)
            if attempt is not None
            else None
        )
        return ReadingPracticeState(
            task=task,
            passage=passage,
            attempt=attempt,
            score=score,
        )


def submit_reading_practice(
    *,
    user_id: int,
    task_id: int,
    answers: Mapping[str, str],
    allow_incomplete: bool = False,
    session_factory: sessionmaker[Session] | None = None,
) -> ReadingPracticeState:
    """Score and persist one final submission, task completion, and study log."""

    factory = session_factory or get_session_factory()
    with session_scope(factory) as session:
        task = get_task(session, user_id=user_id, task_id=task_id)
        if task is None:
            raise ReadingPracticeError("task_not_found")
        passage = resolve_reading_passage(task)
        if passage is None:
            raise ReadingPracticeError("practice_not_found")
        existing = get_task_question_attempt(
            session,
            user_id=user_id,
            task_id=task_id,
        )
        if existing is not None:
            raise ReadingPracticeError("already_submitted")

        expected_ids = {
            question.question_id for question in passage.questions
        }
        if (
            set(answers) - expected_ids
            or (not allow_incomplete and set(answers) != expected_ids)
            or any(
            not isinstance(answer, str) or not normalize_answer(answer)
            for answer in answers.values()
            )
        ):
            raise ReadingPracticeError("incomplete_answers")

        try:
            score = score_reading_answers(passage, answers)
        except ValueError as error:
            raise ReadingPracticeError(str(error)) from error
        attempt = create_task_question_attempt(
            session,
            user_id=user_id,
            task_id=task_id,
            passage_id=passage.passage_id,
            passage_version=passage.version,
            answers_json=json.dumps(
                dict(answers),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            results_json=serialize_reading_score(score),
            score=score.correct_count,
            total_questions=score.total_questions,
            accuracy=score.accuracy,
            incorrect_question_ids_json=json.dumps(
                score.incorrect_question_ids,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        )
        completed_task = set_task_completed(
            session,
            user_id=user_id,
            task_id=task_id,
            actual_minutes=None,
        )
        if completed_task is None:
            raise ReadingPracticeError("task_not_found")
        return ReadingPracticeState(
            task=completed_task,
            passage=passage,
            attempt=attempt,
            score=score,
        )


def list_reading_history(
    user_id: int,
    *,
    limit: int = 100,
    session_factory: sessionmaker[Session] | None = None,
) -> list[ReadingHistoryItem]:
    """Return saved reading outcomes for history and future integrations."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        attempts = list_task_question_attempts(
            session,
            user_id=user_id,
            limit=limit,
        )
        items = []
        for attempt in attempts:
            score = deserialize_reading_score(attempt.results_json)
            items.append(
                ReadingHistoryItem(
                    attempt_id=attempt.id,
                    task_id=attempt.task_id,
                    passage_title=score.passage_title,
                    score=attempt.score,
                    total_questions=attempt.total_questions,
                    accuracy=attempt.accuracy,
                    incorrect_question_ids=score.incorrect_question_ids,
                    submitted_at=attempt.submitted_at,
                )
            )
        return items
