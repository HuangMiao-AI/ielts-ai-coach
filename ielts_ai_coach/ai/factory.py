"""Factory for selecting Qwen or local Mock AI mode."""

from __future__ import annotations

from ielts_ai_coach.ai.base import AIProvider
from ielts_ai_coach.ai.mock import MockAIProvider
from ielts_ai_coach.ai.qwen import QwenAIProvider
from ielts_ai_coach.config import AISettings, get_ai_settings


def get_ai_provider(settings: AISettings | None = None) -> AIProvider:
    """Return Qwen when configured, otherwise the local Mock provider."""

    active_settings = settings or get_ai_settings()
    if not active_settings.api_key:
        return MockAIProvider()
    return QwenAIProvider(active_settings)
