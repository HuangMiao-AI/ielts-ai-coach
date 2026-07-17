"""Tests for AI provider selection, Mock mode, and safe Qwen failures."""

from __future__ import annotations

import requests

from ielts_ai_coach.ai.factory import get_ai_provider
from ielts_ai_coach.ai.mock import MockAIProvider
from ielts_ai_coach.ai.qwen import QwenAIProvider
from ielts_ai_coach.config import AISettings


class TimeoutSession:
    """Fake HTTP session that always times out."""

    def __init__(self) -> None:
        """Initialize a request counter."""

        self.calls = 0

    def post(self, *args: object, **kwargs: object) -> object:
        """Raise a timeout without performing a network request."""

        self.calls += 1
        raise requests.Timeout()


def test_factory_uses_mock_without_api_key() -> None:
    """Missing credentials must select local demonstration mode."""

    settings = AISettings("", "https://example.invalid/v1", "qwen-plus", 5, 0)
    provider = get_ai_provider(settings)

    assert isinstance(provider, MockAIProvider)
    assert provider.is_mock is True
    assert "学习参考" in provider.generate(
        [{"role": "user", "content": "如何提高写作？"}]
    ).content


def test_mock_writing_response_is_valid_json() -> None:
    """Mock writing mode must return the complete structured shape."""

    response = MockAIProvider().generate([], json_mode=True)

    assert '"estimated_overall"' in response.content
    assert "官方IELTS成绩" in response.content


def test_qwen_timeout_is_retried_without_exposing_secret() -> None:
    """Qwen timeouts must use bounded retries and a safe error code."""

    session = TimeoutSession()
    provider = QwenAIProvider(
        AISettings(
            "super-secret-test-key",
            "https://example.invalid/v1",
            "qwen-test",
            5,
            1,
        ),
        http_session=session,  # type: ignore[arg-type]
        sleeper=lambda _: None,
    )

    try:
        provider.generate([{"role": "user", "content": "test"}])
    except Exception as error:
        assert str(error) == "network_unavailable"
        assert "super-secret-test-key" not in str(error)
    else:
        raise AssertionError("A timeout must not be treated as success.")
    assert session.calls == 2
