"""IELTS Level 2 writing feedback validation, persistence, and quotas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.ai.base import AIProvider
from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.ai.writing_evaluator import (
    FeedbackEvaluationError,
    WRITING_DISCLAIMER,
    request_valid_feedback,
)
from ielts_ai_coach.database.connection import get_session_factory, session_scope
from ielts_ai_coach.database.models import Essay, WritingFeedback
from ielts_ai_coach.database.usage_repository import (
    get_daily_usage,
    increment_successful_usage,
)
from ielts_ai_coach.database.writing_repository import (
    create_essay,
    create_writing_feedback,
    get_essay,
    list_essays,
    list_feedback_for_essay,
    set_essay_status,
)


WRITING_DAILY_LIMIT = 3
MAX_PROMPT_LENGTH = 2000
MAX_ESSAY_LENGTH = 12000


class WritingServiceError(ValueError):
    """Raised for safe, user-facing writing workflow failures."""


@dataclass(frozen=True)
class WritingResult:
    """One successful essay evaluation and remaining daily quota."""

    essay: Essay
    feedback: WritingFeedback
    remaining: int
    is_mock: bool


def count_words(content: str) -> int:
    """Count English words and standalone numbers in an essay."""

    return len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*|\d+", content))


def validate_essay_input(
    *,
    test_type: str,
    task_type: str,
    prompt: str,
    content: str,
) -> None:
    """Validate bounded IELTS writing submission fields."""

    if test_type not in {"Academic", "General"}:
        raise WritingServiceError("invalid_test_type")
    if task_type not in {"Task 1", "Task 2"}:
        raise WritingServiceError("invalid_task_type")
    if not 1 <= len(prompt.strip()) <= MAX_PROMPT_LENGTH:
        raise WritingServiceError("invalid_prompt")
    if not 1 <= len(content.strip()) <= MAX_ESSAY_LENGTH:
        raise WritingServiceError("invalid_content")


def get_writing_remaining(
    user_id: int,
    *,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> int:
    """Return a user's remaining successful writing evaluations today."""

    active_date = today or date.today()
    factory = session_factory or get_session_factory()
    with factory() as session:
        usage = get_daily_usage(
            session, user_id=user_id, usage_date=active_date
        )
        used = usage.writing_success_count if usage else 0
        return max(0, WRITING_DAILY_LIMIT - used)


def _evaluate_saved_essay(
    *,
    user_id: int,
    essay_id: int,
    provider: AIProvider,
    active_date: date,
    factory: sessionmaker[Session],
) -> WritingResult:
    """Evaluate one persisted user-owned essay and store valid feedback."""

    with factory() as session:
        essay = get_essay(session, user_id=user_id, essay_id=essay_id)
        if essay is None:
            raise WritingServiceError("essay_not_found")

    try:
        feedback_data, provider_name, model_name = request_valid_feedback(
            provider, essay
        )
    except FeedbackEvaluationError as error:
        with session_scope(factory) as session:
            set_essay_status(
                session,
                user_id=user_id,
                essay_id=essay_id,
                status="failed",
                last_error=str(error),
            )
        raise WritingServiceError(str(error)) from error

    with session_scope(factory) as session:
        owned_essay = set_essay_status(
            session,
            user_id=user_id,
            essay_id=essay_id,
            status="completed",
        )
        if owned_essay is None:
            raise WritingServiceError("essay_not_found")
        feedback = create_writing_feedback(
            session,
            user_id=user_id,
            essay_id=essay_id,
            feedback=feedback_data,
            provider=provider_name,
            model_name=model_name,
        )
        usage = increment_successful_usage(
            session,
            user_id=user_id,
            usage_date=active_date,
            category="writing",
        )
        return WritingResult(
            essay=owned_essay,
            feedback=feedback,
            remaining=max(0, WRITING_DAILY_LIMIT - usage.writing_success_count),
            is_mock=provider.is_mock,
        )


def submit_essay(
    *,
    user_id: int,
    test_type: str,
    task_type: str,
    prompt: str,
    content: str,
    provider: AIProvider | None = None,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> WritingResult:
    """Persist and evaluate a new essay, consuming quota only on success."""

    validate_essay_input(
        test_type=test_type,
        task_type=task_type,
        prompt=prompt,
        content=content,
    )
    active_date = today or date.today()
    factory = session_factory or get_session_factory()
    if get_writing_remaining(
        user_id, today=active_date, session_factory=factory
    ) <= 0:
        raise WritingServiceError("quota_exhausted")
    with session_scope(factory) as session:
        essay = create_essay(
            session,
            user_id=user_id,
            test_type=test_type,
            task_type=task_type,
            prompt=prompt.strip(),
            content=content.strip(),
            word_count=count_words(content),
        )
        essay_id = essay.id
    return _evaluate_saved_essay(
        user_id=user_id,
        essay_id=essay_id,
        provider=provider or get_ai_provider(),
        active_date=active_date,
        factory=factory,
    )


def retry_essay(
    *,
    user_id: int,
    essay_id: int,
    provider: AIProvider | None = None,
    today: date | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> WritingResult:
    """Retry a failed user-owned essay without creating a duplicate essay."""

    active_date = today or date.today()
    factory = session_factory or get_session_factory()
    with factory() as session:
        essay = get_essay(session, user_id=user_id, essay_id=essay_id)
        if essay is None:
            raise WritingServiceError("essay_not_found")
        if essay.status != "failed":
            raise WritingServiceError("essay_not_retryable")
    if get_writing_remaining(
        user_id, today=active_date, session_factory=factory
    ) <= 0:
        raise WritingServiceError("quota_exhausted")
    return _evaluate_saved_essay(
        user_id=user_id,
        essay_id=essay_id,
        provider=provider or get_ai_provider(),
        active_date=active_date,
        factory=factory,
    )


def get_essay_history(
    user_id: int,
    *,
    session_factory: sessionmaker[Session] | None = None,
) -> list[Essay]:
    """Return essays owned by one user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return list_essays(session, user_id=user_id)


def get_essay_feedback(
    *,
    user_id: int,
    essay_id: int,
    session_factory: sessionmaker[Session] | None = None,
) -> list[WritingFeedback]:
    """Return feedback only for an essay owned by the user."""

    factory = session_factory or get_session_factory()
    with factory() as session:
        return list_feedback_for_essay(
            session, user_id=user_id, essay_id=essay_id
        )
