"""Tests for coach context isolation, quotas, failures, and clearing."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from ielts_ai_coach.ai.base import AIProvider, AIProviderError, AIResponse
from ielts_ai_coach.ai.mock import MockAIProvider
from ielts_ai_coach.auth import register_user
from ielts_ai_coach.database.coach_repository import create_coach_message
from ielts_ai_coach.database.connection import session_scope
from ielts_ai_coach.services.coaching import (
    COACH_DAILY_LIMIT,
    CoachServiceError,
    clear_current_conversation,
    get_coach_remaining,
    get_visible_messages,
    send_coach_message,
)
from ielts_ai_coach.services.profiles import save_profile
from ielts_ai_coach.services.scores import save_score_record


class CapturingProvider(AIProvider):
    """Fake provider that stores the messages it receives."""

    def __init__(self) -> None:
        """Initialize an empty capture."""

        self.messages: list[dict[str, str]] = []

    @property
    def provider_name(self) -> str:
        """Return the provider name."""

        return "capture"

    @property
    def model_name(self) -> str:
        """Return the model name."""

        return "capture-v1"

    @property
    def is_mock(self) -> bool:
        """Return true because this provider is local."""

        return True

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
    ) -> AIResponse:
        """Capture messages and return a fixed response."""

        self.messages = messages
        return AIResponse("请按计划完成弱项练习。", "capture", "capture-v1")


class FailingProvider(CapturingProvider):
    """Fake provider that always fails safely."""

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
    ) -> AIResponse:
        """Raise a safe provider error."""

        raise AIProviderError("network_unavailable")


def _create_student(
    username: str,
    nickname: str,
    session_factory: sessionmaker[Session],
    today: date,
) -> int:
    """Create one student with owned profile and score data."""

    user_id = register_user(
        username,
        "secure-pass-01",
        state={},
        session_factory=session_factory,
    ).id
    save_profile(
        user_id=user_id,
        nickname=nickname,
        grade="高二",
        target_overall=7.0,
        exam_date=today + timedelta(days=80),
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
    return user_id


def test_coach_context_contains_only_current_user(
    session_factory: sessionmaker[Session],
) -> None:
    """A provider prompt must not contain another user's profile data."""

    today = date(2026, 7, 16)
    first_id = _create_student("CoachOne", "小星", session_factory, today)
    _create_student("CoachTwo", "绝密昵称", session_factory, today)
    provider = CapturingProvider()

    reply = send_coach_message(
        user_id=first_id,
        content="我应该先练什么？",
        provider=provider,
        today=today,
        session_factory=session_factory,
    )
    prompt = "\n".join(message["content"] for message in provider.messages)

    assert "小星" in prompt
    assert "绝密昵称" not in prompt
    assert reply.remaining == COACH_DAILY_LIMIT - 1
    assert "不替代正式教师指导" in reply.message.content


def test_failed_coach_call_does_not_consume_quota(
    session_factory: sessionmaker[Session],
) -> None:
    """Provider failure must keep the successful-call quota unchanged."""

    today = date(2026, 7, 16)
    user_id = _create_student("CoachFail", "失败测试", session_factory, today)

    with pytest.raises(CoachServiceError, match="network_unavailable"):
        send_coach_message(
            user_id=user_id,
            content="测试失败",
            provider=FailingProvider(),
            today=today,
            session_factory=session_factory,
        )

    assert get_coach_remaining(
        user_id, today=today, session_factory=session_factory
    ) == COACH_DAILY_LIMIT


def test_coach_quota_and_clear_are_user_scoped(
    session_factory: sessionmaker[Session],
) -> None:
    """Quota and visible conversation state must be isolated by user."""

    today = date(2026, 7, 16)
    first_id = _create_student("QuotaOne", "用户一", session_factory, today)
    second_id = _create_student("QuotaTwo", "用户二", session_factory, today)

    for index in range(COACH_DAILY_LIMIT):
        send_coach_message(
            user_id=first_id,
            content=f"问题 {index}",
            provider=MockAIProvider(),
            today=today,
            session_factory=session_factory,
        )
    with pytest.raises(CoachServiceError, match="quota_exhausted"):
        send_coach_message(
            user_id=first_id,
            content="超额问题",
            provider=MockAIProvider(),
            today=today,
            session_factory=session_factory,
        )

    send_coach_message(
        user_id=second_id,
        content="我的问题",
        provider=MockAIProvider(),
        today=today,
        session_factory=session_factory,
    )
    assert clear_current_conversation(
        first_id, session_factory=session_factory
    ) == 40
    assert get_visible_messages(
        first_id, session_factory=session_factory
    ) == []
    assert len(
        get_visible_messages(second_id, session_factory=session_factory)
    ) == 2


def test_context_uses_only_six_recent_messages(
    session_factory: sessionmaker[Session],
) -> None:
    """The model prompt must not receive an unbounded conversation history."""

    today = date(2026, 7, 16)
    user_id = _create_student("RecentSix", "近六条", session_factory, today)
    with session_scope(session_factory) as session:
        for index in range(8):
            create_coach_message(
                session,
                user_id=user_id,
                role="user" if index % 2 == 0 else "assistant",
                content=f"历史消息{index}",
            )
    provider = CapturingProvider()

    send_coach_message(
        user_id=user_id,
        content="新的问题",
        provider=provider,
        today=today,
        session_factory=session_factory,
    )
    history_content = "\n".join(
        message["content"] for message in provider.messages[1:-1]
    )

    assert len(provider.messages) == 8
    assert "历史消息0" not in history_content
    assert "历史消息1" not in history_content
    assert "历史消息2" in history_content


def test_clear_hides_more_than_one_hundred_visible_messages(
    session_factory: sessionmaker[Session],
) -> None:
    """Clearing a conversation must not leave older visible messages."""

    today = date(2026, 7, 16)
    user_id = _create_student("ClearAll", "全部清理", session_factory, today)
    with session_scope(session_factory) as session:
        for index in range(105):
            create_coach_message(
                session,
                user_id=user_id,
                role="user",
                content=f"消息{index}",
            )

    assert clear_current_conversation(
        user_id, session_factory=session_factory
    ) == 105
    assert get_visible_messages(
        user_id, session_factory=session_factory
    ) == []
