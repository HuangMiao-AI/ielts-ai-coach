"""Alibaba Cloud Model Studio Qwen OpenAI-compatible provider."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import requests

from ielts_ai_coach.ai.base import AIProvider, AIProviderError, AIResponse
from ielts_ai_coach.config import AISettings


LOGGER = logging.getLogger(__name__)


class QwenAIProvider(AIProvider):
    """Call a configured Qwen OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        settings: AISettings,
        *,
        http_session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialize the provider without logging secret configuration."""

        if not settings.api_key:
            raise ValueError("Qwen API key is required.")
        self._settings = settings
        self._session = http_session or requests.Session()
        self._sleeper = sleeper

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""

        return "qwen"

    @property
    def model_name(self) -> str:
        """Return the configured Qwen model."""

        return self._settings.model_name

    @property
    def is_mock(self) -> bool:
        """Return false for the network provider."""

        return False

    def _request_payload(
        self,
        messages: list[dict[str, str]],
        json_mode: bool,
    ) -> dict[str, Any]:
        """Build one OpenAI-compatible request payload."""

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.3,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def generate(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
    ) -> AIResponse:
        """Generate a response with bounded retry and safe errors."""

        endpoint = f"{self._settings.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._request_payload(messages, json_mode)
        attempts = self._settings.max_retries + 1

        for attempt in range(attempts):
            try:
                response = self._session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self._settings.timeout_seconds,
                )
            except (requests.Timeout, requests.ConnectionError) as error:
                if attempt + 1 < attempts:
                    self._sleeper(min(0.25 * (2**attempt), 1.0))
                    continue
                LOGGER.warning("AI request failed with a retryable network error.")
                raise AIProviderError("network_unavailable") from error
            except requests.RequestException as error:
                LOGGER.warning("AI request failed before receiving a response.")
                raise AIProviderError("request_failed") from error

            if response.status_code >= 500 and attempt + 1 < attempts:
                self._sleeper(min(0.25 * (2**attempt), 1.0))
                continue
            if response.status_code >= 400:
                LOGGER.warning("AI provider returned HTTP %s.", response.status_code)
                raise AIProviderError("provider_rejected_request")

            try:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError) as error:
                LOGGER.warning("AI provider returned an invalid response shape.")
                raise AIProviderError("invalid_provider_response") from error
            if not isinstance(content, str) or not content.strip():
                raise AIProviderError("empty_provider_response")
            return AIResponse(
                content=content.strip(),
                provider=self.provider_name,
                model_name=self.model_name,
            )

        raise AIProviderError("request_failed")
