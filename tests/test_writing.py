"""Tests for Level 2 writing feedback, retries, quotas, and isolation."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.ai.base import AIProvider, AIResponse
from ielts_ai_coach.ai.mock import MockAIProvider
from ielts_ai_coach.ai.schemas import WritingFeedbackSchema
from ielts_ai_coach.auth import register_user
from ielts_ai_coach.services.writing import (
    WRITING_DAILY_LIMIT,
    WritingServiceError,
    get_essay_feedback,
    get_essay_history,
    get_writing_remaining,
    retry_essay,
    submit_essay,
)


class SequenceProvider(AIProvider):
    """Return a configured sequence of local response strings."""

    def __init__(self, responses: list[str]) -> None:
        """Store responses and initialize the call counter."""

        self.responses = responses
        self.calls = 0

    @property
    def provider_name(self) -> str:
        """Return the provider name."""

        return "sequence"

    @property
    def model_name(self) -> str:
        """Return the model name."""

        return "sequence-v1"

    @property
    def is_mock(self) -> bool:
        """Return true because no network is used."""

        return True

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
    ) -> AIResponse:
        """Return the next configured response."""

        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return AIResponse(
            self.responses[index], self.provider_name, self.model_name
        )


def _create_user(
    username: str, session_factory: sessionmaker[Session]
) -> int:
    """Create one test user."""

    return register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id


def _submit(
    user_id: int,
    session_factory: sessionmaker[Session],
    provider: AIProvider,
    today: date,
):
    """Submit a valid test essay."""

    return submit_essay(
        user_id=user_id,
        test_type="Academic",
        task_type="Task 2",
        prompt="Some people think schools should teach practical skills. Discuss.",
        content=(
            "Schools can teach practical skills because students need them in "
            "daily life. This approach also connects knowledge with experience."
        ),
        provider=provider,
        today=today,
        session_factory=session_factory,
    )


def test_writing_schema_rejects_non_half_band() -> None:
    """Structured scores must use valid IELTS half-band increments."""

    data = {
        "task_response_or_achievement": 6.2,
        "coherence_and_cohesion": 6.0,
        "lexical_resource": 6.0,
        "grammatical_range_and_accuracy": 6.0,
        "estimated_overall": 6.0,
        "strengths": ["Clear position"],
        "main_issues": ["Limited support"],
        "actionable_suggestions": ["Add one example"],
        "rewrite_example": "This paragraph gives a clearer supporting example.",
        "disclaimer": "This is an AI estimate, not an official score.",
    }

    with pytest.raises(ValueError):
        WritingFeedbackSchema.model_validate(data)


def test_invalid_json_is_retried_once_and_saved(
    session_factory: sessionmaker[Session],
) -> None:
    """One malformed response must be repaired with exactly one retry."""

    user_id = _create_user("WritingRepair", session_factory)
    valid_json = MockAIProvider().generate([], json_mode=True).content
    provider = SequenceProvider(["not-json", valid_json])
    result = _submit(
        user_id, session_factory, provider, date(2026, 7, 16)
    )

    assert provider.calls == 2
    assert result.essay.status == "completed"
    assert result.feedback.estimated_overall == 6.0
    assert result.feedback.disclaimer == "该评分为AI预估，不是官方IELTS成绩。"


def test_invalid_json_failure_keeps_essay_and_quota(
    session_factory: sessionmaker[Session],
) -> None:
    """Two invalid responses must preserve a failed essay without charging."""

    today = date(2026, 7, 16)
    user_id = _create_user("WritingFail", session_factory)
    provider = SequenceProvider(["bad", "still bad"])

    with pytest.raises(WritingServiceError, match="invalid_ai_json"):
        _submit(user_id, session_factory, provider, today)

    history = get_essay_history(user_id, session_factory=session_factory)
    assert len(history) == 1
    assert history[0].status == "failed"
    assert get_writing_remaining(
        user_id, today=today, session_factory=session_factory
    ) == WRITING_DAILY_LIMIT


def test_writing_quota_and_essay_isolation(
    session_factory: sessionmaker[Session],
) -> None:
    """Writing history, feedback, and quota must be isolated by user."""

    today = date(2026, 7, 16)
    owner_id = _create_user("WritingOwner", session_factory)
    other_id = _create_user("WritingOther", session_factory)
    latest = None
    for _ in range(WRITING_DAILY_LIMIT):
        latest = _submit(owner_id, session_factory, MockAIProvider(), today)
    assert latest is not None

    with pytest.raises(WritingServiceError, match="quota_exhausted"):
        _submit(owner_id, session_factory, MockAIProvider(), today)

    assert get_essay_history(other_id, session_factory=session_factory) == []
    assert get_essay_feedback(
        user_id=other_id,
        essay_id=latest.essay.id,
        session_factory=session_factory,
    ) == []


def test_completed_essay_cannot_use_failure_retry(
    session_factory: sessionmaker[Session],
) -> None:
    """Retry must be limited to failed user-owned essays."""

    today = date(2026, 7, 16)
    user_id = _create_user("WritingCompleted", session_factory)
    result = _submit(user_id, session_factory, MockAIProvider(), today)

    with pytest.raises(WritingServiceError, match="essay_not_retryable"):
        retry_essay(
            user_id=user_id,
            essay_id=result.essay.id,
            provider=MockAIProvider(),
            today=today,
            session_factory=session_factory,
        )
